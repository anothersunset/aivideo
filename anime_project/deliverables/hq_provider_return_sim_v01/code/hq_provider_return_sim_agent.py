#!/usr/bin/env python3
"""TASK-058 HQProviderReturnSimAgent.

Generate SIMULATED high-quality provider-return MP4s into the external inbox.
NO external API call. NO HTTP submit/poll. NO API key. NO secrets.

The current-demo HQ launch manifest is the source of truth. This keeps the
simulation aligned with the operator handoff package and the Hub UI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

from pipeline_common import (
    FPS,
    HEIGHT,
    WIDTH,
    resolve_workspace_path,
    run_checked,
)


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME = WORKSPACE / "anime_project"
PIPE = ANIME / "pipeline"
TOOL_JOBS = PIPE / "tool_jobs"
INBOX = PIPE / "external_results" / "inbox"
LAUNCH_MANIFEST = PIPE / "provider_launch" / "current_demo_hq_v01" / "high_quality_provider_launch_manifest.json"
LOCAL_POLISH_MANIFEST = PIPE / "polish_outputs" / "local_remotion" / "local_polish_render_manifest.json"
HUB_OUTPUT_DIR = PIPE / "provider_returns" / "current_demo_hq_v01"
FRAMES_DIR = HUB_OUTPUT_DIR / "review_frames"
HUB_MANIFEST = HUB_OUTPUT_DIR / "hq_provider_return_sim_manifest.json"
REPORT_PATH = HUB_OUTPUT_DIR / "hq_provider_return_sim_report.md"
CHAIN_MANIFEST = PIPE / "external_results" / "manifests" / "simulated_hq_provider_returns.json"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jobs(segment: str) -> list[dict]:
    return load_json(TOOL_JOBS / segment / "shot_jobs.json", {}).get("jobs", [])


def find_job(segment: str, shot_id: str) -> dict:
    for job in load_jobs(segment):
        if job.get("shot_id") == shot_id:
            return job
    raise KeyError(f"{segment}/{shot_id} not in shot_jobs.json")


def local_polish_lookup() -> dict[tuple[str, str], dict]:
    manifest = load_json(LOCAL_POLISH_MANIFEST, {})
    return {
        (item.get("segment", ""), item.get("shot_id", "")): item
        for item in manifest.get("renders", [])
        if item.get("accepted") and item.get("output")
    }


def find_source_video(row: dict, polish: dict[tuple[str, str], dict]) -> tuple[str, str]:
    key = (row["segment"], row["shot_id"])
    if key in polish:
        return polish[key]["output"], "local_polish_render"
    job = find_job(row["segment"], row["shot_id"])
    return job["current_local_output"], "tool_job_current_local_output"


def provider_vf(provider: str) -> str:
    grades = {
        "kling_i2v": "eq=contrast=1.13:saturation=0.88:brightness=-0.018,unsharp=5:5:0.60,noise=alls=2:allf=t",
        "pika": "eq=contrast=1.08:saturation=1.02:brightness=0.004,unsharp=3:3:0.42,noise=alls=1:allf=t",
        "runway": "eq=contrast=1.10:saturation=0.92:brightness=-0.015,unsharp=3:3:0.55",
        "seedance_i2v": "eq=contrast=1.14:saturation=0.88:brightness=-0.025,unsharp=5:5:0.60",
    }
    grade = grades.get(provider, "eq=contrast=1.08:saturation=0.92,unsharp=3:3:0.45")
    return (
        f"fps={FPS},scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},{grade},format=yuv420p"
    )


def ffprobe_video(path: Path) -> dict:
    result = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        cwd=str(WORKSPACE),
        capture_text=True,
    )
    data = json.loads(result.stdout)
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    fmt = data.get("format", {})
    return {
        "codec_name": video.get("codec_name", ""),
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
        "r_frame_rate": video.get("r_frame_rate", ""),
        "avg_frame_rate": video.get("avg_frame_rate", ""),
        "nb_frames": int(video.get("nb_frames", 0) or 0) if str(video.get("nb_frames", "")).isdigit() else 0,
        "duration_seconds": float(fmt.get("duration", 0) or 0),
        "size_bytes": int(fmt.get("size", 0) or 0),
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


def extract_frame(video: Path, row: dict, duration: float) -> str:
    frame = FRAMES_DIR / row["provider"] / row["segment"] / f"{row['shot_id']}_{row['provider']}_sim_mid.png"
    frame.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{max(0.1, duration / 2):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(frame),
        ],
        cwd=str(WORKSPACE),
    )
    return rel(frame)


def render_return(row: dict, task_id: str, polish: dict[tuple[str, str], dict]) -> dict:
    source_raw, source_mode = find_source_video(row, polish)
    source = resolve_workspace_path(WORKSPACE, source_raw)
    if not source.exists():
        raise FileNotFoundError(f"source video not found: {source}")
    duration = float(row.get("duration_seconds", 0) or find_job(row["segment"], row["shot_id"]).get("duration_seconds", 0))
    output = resolve_workspace_path(WORKSPACE, row["expected_return_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            provider_vf(row["provider"]),
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-an",
            "-movflags",
            "+faststart",
            str(output),
        ],
        cwd=str(WORKSPACE),
    )
    probe = ffprobe_video(output)
    review_frame = extract_frame(output, row, duration)
    metrics = image_metrics(WORKSPACE / review_frame)
    checks = {
        "exists": output.exists() and output.stat().st_size > 0,
        "h264": probe["codec_name"] == "h264",
        "resolution_1920x1080": probe["width"] == WIDTH and probe["height"] == HEIGHT,
        "fps_24": probe["r_frame_rate"] == "24/1",
        "duration_close": abs(probe["duration_seconds"] - duration) <= max(0.5, duration * 0.08),
        "non_empty": probe["size_bytes"] > 100_000,
        "nonblank_frame": metrics["nonblank"],
    }
    accepted = all(checks.values())
    return {
        "task_id": task_id,
        "queue_id": row.get("queue_id", ""),
        "provider": row["provider"],
        "segment": row["segment"],
        "shot_id": row["shot_id"],
        "label": row.get("label", ""),
        "source": rel(source),
        "source_video": source_raw,
        "source_mode": source_mode,
        "output": rel(output),
        "expected_return_path": row["expected_return_path"],
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "target_duration_seconds": round(duration, 3),
        "actual_duration_seconds": round(probe["duration_seconds"], 3),
        "duration_seconds": duration,
        "probe": probe,
        "review_frame": review_frame,
        "frame_metrics": metrics,
        "checks": checks,
        "accepted": accepted,
        "status": "simulated_provider_return_ready" if accepted else "simulated_provider_return_needs_repair",
        "mode": "simulated_provider_return_no_external_api_call",
        "external_api_called": False,
        "simulation_notice": "simulated_provider_return_no_external_api_call",
        "risk_rules": row.get("risk_rules", []),
        "safety_notes": row.get("safety_notes", []),
    }


def contact_sheet(returns: list[dict]) -> str:
    thumb_w, thumb_h = 384, 216
    label_h = 72
    columns = 2
    rows = (len(returns) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), (18, 20, 22))
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(returns):
        x = (index % columns) * thumb_w
        y = (index // columns) * (thumb_h + label_h)
        with Image.open(WORKSPACE / item["review_frame"]) as frame:
            sheet.paste(frame.convert("RGB").resize((thumb_w, thumb_h)), (x, y))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill=(28, 31, 34))
        draw.text((x + 12, y + thumb_h + 10), f"{item['provider']} | {item['segment']} / {item['shot_id']}", fill=(240, 240, 235))
        draw.text((x + 12, y + thumb_h + 34), item["status"], fill=(182, 190, 198))
        draw.text((x + 12, y + thumb_h + 54), "simulated return, no external API", fill=(150, 160, 170))
    output = FRAMES_DIR / "hq_provider_return_sim_contact_sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return rel(output)


def build_report(manifest: dict) -> str:
    lines = [
        "# HQ Provider Return Simulation Report",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Mode: {manifest['mode']}",
        f"Generated returns: {manifest['generated_count']}",
        f"Accepted returns: {manifest['accepted_count']}",
        f"Contact sheet: {manifest['contact_sheet']}",
        "",
        "## Important Notice",
        "",
        "These MP4 files simulate provider returns for pipeline validation. No external provider API call was made.",
        "",
        "| Provider | Shot | Duration | Status | Inbox Output |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in manifest["returns"]:
        lines.append(
            f"| {item['provider']} | {item['segment']} / {item['shot_id']} | "
            f"{item['duration_seconds']}s | {item['status']} | {item['output']} |"
        )
    lines.extend(["", "## Next Step", "", manifest["next_step"]])
    return "\n".join(lines)


def launch_rows() -> list[dict]:
    launch = load_json(LAUNCH_MANIFEST, {})
    rows = launch.get("launch_rows", [])
    if not rows:
        raise ValueError(f"no launch_rows found in {LAUNCH_MANIFEST}")
    return rows


def run_simulation(task_id: str) -> dict:
    rows = launch_rows()
    polish = local_polish_lookup()
    returns = [render_return(row, task_id, polish) for row in rows]
    sheet = contact_sheet(returns)
    accepted_count = sum(1 for item in returns if item["accepted"])
    provider_counts: dict[str, int] = {}
    for item in returns:
        provider_counts[item["provider"]] = provider_counts.get(item["provider"], 0) + 1
    manifest = {
        "task_id": task_id,
        "stage": "hq_provider_return_simulation",
        "mode": "simulated_provider_return_no_external_api_call",
        "external_api_called": False,
        "decision": "simulated_provider_returns_ready_for_ingest"
        if accepted_count == len(returns) and returns
        else "simulated_provider_returns_need_repair",
        "source_launch_manifest": rel(LAUNCH_MANIFEST),
        "source_local_polish_manifest": rel(LOCAL_POLISH_MANIFEST) if LOCAL_POLISH_MANIFEST.exists() else "",
        "return_count": len(returns),
        "generated_count": len(returns),
        "accepted_count": accepted_count,
        "rejected_count": len(returns) - accepted_count,
        "provider_counts": provider_counts,
        "contact_sheet": sheet,
        "returns": returns,
        "report": rel(REPORT_PATH),
        "next_step": "Run ExternalResultIngestAgent, ExternalResultReviewAgent, then ShotReplacementAgent to rehearse provider return backfill.",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    write_json(HUB_MANIFEST, manifest)
    write_json(CHAIN_MANIFEST, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-058")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_simulation(args.task_id)
    if args.quiet:
        print(rel(HUB_MANIFEST))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
