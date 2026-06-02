from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments"
POLISH_QUEUE_PATH = PIPELINE_DIR / "polish_queue" / "polish_queue_manifest.json"
OUTPUT_DIR = PIPELINE_DIR / "polish_outputs" / "local_remotion"
FRAMES_DIR = OUTPUT_DIR / "review_frames"
MANIFEST_PATH = OUTPUT_DIR / "local_polish_render_manifest.json"
REPORT_PATH = OUTPUT_DIR / "local_polish_render_report.md"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_project_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE / path


def load_segment_manifest(segment: str) -> dict:
    replacement_path = SEGMENT_DIR / segment / "manifest_with_replacements.json"
    if replacement_path.exists():
        return load_json(replacement_path, {})
    return load_json(SEGMENT_DIR / segment / "manifest.json", {})


def find_source_video(segment: str, shot_id: str) -> str:
    manifest = load_segment_manifest(segment)
    for shot in manifest.get("shots", []):
        if shot.get("shot_id") == shot_id:
            return shot.get("video", "")
    raise KeyError(f"{segment}/{shot_id}")


def ffprobe_video(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate,duration",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    data = json.loads(result.stdout)
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    return {
        "codec_name": video.get("codec_name", ""),
        "width": video.get("width", 0),
        "height": video.get("height", 0),
        "avg_frame_rate": video.get("avg_frame_rate", ""),
        "duration_seconds": float(data.get("format", {}).get("duration") or video.get("duration") or 0),
    }


def image_metrics(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        small = rgb.resize((96, 54))
        gray = small.convert("L")
        stat = ImageStat.Stat(gray)
        extrema = gray.getextrema()
        colors = small.getcolors(maxcolors=96 * 54)
        unique_colors = len(colors or [])
        return {
            "width": rgb.width,
            "height": rgb.height,
            "mean_luma": round(float(stat.mean[0]), 3),
            "stddev_luma": round(float(stat.stddev[0]), 3),
            "luma_min": int(extrema[0]),
            "luma_max": int(extrema[1]),
            "unique_color_sample_count": unique_colors,
            "nonblank": float(stat.stddev[0]) >= 2.0 and unique_colors >= 12 and (extrema[1] - extrema[0]) >= 8,
        }


def polish_filter(item: dict) -> str:
    shot_id = item.get("shot_id", "")
    grade = {
        "ON-008": "eq=contrast=1.22:saturation=0.80:brightness=-0.035",
        "08-003": "eq=contrast=1.16:saturation=0.82:brightness=-0.02",
        "08-004": "eq=contrast=1.24:saturation=0.78:brightness=-0.04",
        "11-004": "eq=contrast=1.15:saturation=0.88:brightness=-0.015",
        "12-002": "eq=contrast=1.10:saturation=0.92:brightness=-0.01",
    }.get(shot_id, "eq=contrast=1.12:saturation=0.88:brightness=-0.015")
    return (
        "fps=24,"
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,"
        f"{grade},"
        "unsharp=5:5:0.70,"
        "noise=alls=3:allf=t,"
        "vignette=PI/6,"
        "format=yuv420p"
    )


def render_item(item: dict, task_id: str) -> dict:
    segment = item["segment"]
    shot_id = item["shot_id"]
    source_raw = find_source_video(segment, shot_id)
    source = resolve_project_path(source_raw)
    if not source or not source.exists():
        raise FileNotFoundError(source_raw)
    duration = float(item.get("duration_seconds", 0) or 0)
    output = OUTPUT_DIR / segment / shot_id / f"{shot_id}_local_polish.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            polish_filter(item),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    frame_path = FRAMES_DIR / segment / f"{shot_id}_local_polish_mid.png"
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{max(0.1, duration / 2):.3f}",
            "-i",
            str(output),
            "-frames:v",
            "1",
            str(frame_path),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    probe = ffprobe_video(output)
    metrics = image_metrics(frame_path)
    checks = {
        "exists": output.exists() and output.stat().st_size > 0,
        "h264": probe["codec_name"] == "h264",
        "resolution_1920x1080": probe["width"] == 1920 and probe["height"] == 1080,
        "fps_24": probe["avg_frame_rate"] == "24/1",
        "duration_matches": abs(probe["duration_seconds"] - duration) <= 0.15,
        "nonblank_frame": metrics["nonblank"],
    }
    return {
        "task_id": task_id,
        "queue_id": item["queue_id"],
        "segment": segment,
        "shot_id": shot_id,
        "priority": item.get("priority", ""),
        "source_video": source_raw,
        "source_frame": item.get("source_frame", ""),
        "output": rel(output),
        "review_frame": rel(frame_path),
        "duration_seconds": duration,
        "probe": probe,
        "frame_metrics": metrics,
        "checks": checks,
        "accepted": all(checks.values()),
        "status": "local_polish_candidate_ready" if all(checks.values()) else "local_polish_candidate_needs_repair",
        "notes": "Local Remotion-style polish candidate; no paid provider call was made.",
    }


def contact_sheet(renders: list[dict]) -> str:
    thumb_w, thumb_h = 384, 216
    label_h = 64
    columns = 2
    rows = (len(renders) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), (18, 20, 22))
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(renders):
        x = (index % columns) * thumb_w
        y = (index // columns) * (thumb_h + label_h)
        with Image.open(WORKSPACE / item["review_frame"]) as frame:
            sheet.paste(frame.convert("RGB").resize((thumb_w, thumb_h)), (x, y))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill=(28, 31, 34))
        draw.text((x + 12, y + thumb_h + 10), f"{item['queue_id']} | {item['segment']} / {item['shot_id']}", fill=(240, 240, 235))
        draw.text((x + 12, y + thumb_h + 34), f"{item['status']} | nonblank={item['frame_metrics']['nonblank']}", fill=(182, 190, 198))
    output = FRAMES_DIR / "local_polish_contact_sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return rel(output)


def build_report(manifest: dict) -> str:
    lines = [
        "# Local Polish Render Report",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Rendered candidates: {manifest['rendered_count']}",
        f"Accepted candidates: {manifest['accepted_count']}",
        f"Contact sheet: {manifest['contact_sheet']}",
        "",
        "| Queue | Shot | Duration | Status | Output |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in manifest["renders"]:
        lines.append(
            f"| {item['queue_id']} | {item['segment']} / {item['shot_id']} | "
            f"{item['duration_seconds']}s | {item['status']} | {item['output']} |"
        )
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "Run a review/promote pass to compare these local polish candidates against the current master shots before replacement edit.",
        ]
    )
    return "\n".join(lines)


def run_local_polish(task_id: str) -> dict:
    queue_manifest = load_json(POLISH_QUEUE_PATH, {})
    queue = queue_manifest.get("queue", [])
    renders = [render_item(item, task_id) for item in queue]
    sheet = contact_sheet(renders)
    accepted_count = sum(1 for item in renders if item["accepted"])
    manifest = {
        "task_id": task_id,
        "stage": "local_polish_render",
        "mode": "local_remotion_style_no_external_api_call",
        "decision": "local_polish_candidates_ready" if accepted_count == len(renders) and renders else "local_polish_candidates_need_repair",
        "source_polish_queue": rel(POLISH_QUEUE_PATH),
        "rendered_count": len(renders),
        "accepted_count": accepted_count,
        "rejected_count": len(renders) - accepted_count,
        "contact_sheet": sheet,
        "renders": renders,
        "report": rel(REPORT_PATH),
        "next_step": "Review local polish candidates, then promote accepted clips into replacement manifests.",
    }
    write_json(MANIFEST_PATH, manifest)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-LOCAL-POLISH")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_local_polish(args.task_id)
    if args.quiet:
        print(rel(MANIFEST_PATH))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
