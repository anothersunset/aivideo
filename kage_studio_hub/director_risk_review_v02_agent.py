from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
REVIEW_DIR = PIPELINE_DIR / "director_review_v02"
FRAMES_DIR = REVIEW_DIR / "keyframes"

MASTER_MANIFEST_PATH = SEGMENT_DIR / "master_preview" / "manifest_with_local_polish.json"
PRODUCER_DEMO_V02_PATH = ANIME_PROJECT / "deliverables" / "producer_demo_v02" / "producer_demo_v02_manifest.json"
SEGMENTS = ["onsen_01_sample", "act2_01_sample"]

REVIEW_SHOTS = [
    {
        "segment": "onsen_01_sample",
        "shot_id": "ON-008",
        "label": "Onsen local-polish action test",
        "review_focus": "Local-polish promotion traceability, action readability, rain/silhouette energy.",
        "risk_rules": ["Confirm this remains a local-polish demo candidate, not final character-style approval."],
    },
    {
        "segment": "act2_01_sample",
        "shot_id": "08-003",
        "label": "Rating-risk hidden impact",
        "review_focus": "No face, no pain expression, action clarity through body/prop language.",
        "risk_rules": ["08-003 must not show face or pain expression."],
    },
    {
        "segment": "act2_01_sample",
        "shot_id": "08-004",
        "label": "Iron centipede local-polish test",
        "review_focus": "Promoted local-polish continuity, creature silhouette, edit rhythm.",
        "risk_rules": ["Local-polish candidate must remain traceable to an accepted render."],
    },
    {
        "segment": "act2_01_sample",
        "shot_id": "11-004",
        "label": "Hirumaru parasite limit",
        "review_focus": "Parasite staging must remain readable without escalating body horror.",
        "risk_rules": ["11-004 parasite count limit: 8."],
    },
    {
        "segment": "act2_01_sample",
        "shot_id": "12-002",
        "label": "Chiyo restraint beat",
        "review_focus": "Silent emotional expression through props/hands; avoid pain-process depiction.",
        "risk_rules": ["12-001 to 12-003 must not show a child pain process."],
    },
]


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


def extract_frame(video_path: Path, timestamp: float, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(output_path),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def image_metrics(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        small = rgb.resize((96, 54))
        gray = small.convert("L")
        stat = ImageStat.Stat(gray)
        extrema = gray.getextrema()
        colors = small.getcolors(maxcolors=96 * 54)
        unique_colors = len(colors or [])
        stddev_luma = float(stat.stddev[0])
        return {
            "width": rgb.width,
            "height": rgb.height,
            "mean_luma": round(float(stat.mean[0]), 3),
            "stddev_luma": round(stddev_luma, 3),
            "luma_min": int(extrema[0]),
            "luma_max": int(extrema[1]),
            "unique_color_sample_count": unique_colors,
            "nonblank": stddev_luma >= 2.0 and unique_colors >= 12 and (extrema[1] - extrema[0]) >= 8,
        }


def load_segment_manifest(segment: str) -> dict:
    local_polish_path = SEGMENT_DIR / segment / "manifest_with_local_polish.json"
    if local_polish_path.exists():
        return load_json(local_polish_path, {})
    return load_json(SEGMENT_DIR / segment / "manifest.json", {})


def segment_offsets(manifests: dict[str, dict]) -> dict[str, float]:
    offsets = {}
    cursor = 0.0
    for segment in SEGMENTS:
        offsets[segment] = cursor
        cursor += float(manifests.get(segment, {}).get("duration_seconds", 0) or 0)
    return offsets


def shot_start_times(segment_manifest: dict) -> dict[str, float]:
    starts = {}
    cursor = 0.0
    for shot in segment_manifest.get("shots", []):
        shot_id = shot.get("shot_id")
        if shot_id:
            starts[shot_id] = cursor
        cursor += float(shot.get("duration_seconds", 0) or 0)
    return starts


def find_shot(segment_manifest: dict, shot_id: str) -> dict:
    for shot in segment_manifest.get("shots", []):
        if shot.get("shot_id") == shot_id:
            return shot
    raise KeyError(f"{segment_manifest.get('video', 'segment')}/{shot_id}")


def review_keyframes(task_id: str, master_video: Path, segment_manifests: dict[str, dict]) -> list[dict]:
    offsets = segment_offsets(segment_manifests)
    starts_by_segment = {segment: shot_start_times(manifest) for segment, manifest in segment_manifests.items()}
    reviewed = []
    for item in REVIEW_SHOTS:
        segment = item["segment"]
        shot_id = item["shot_id"]
        shot = find_shot(segment_manifests[segment], shot_id)
        duration = float(shot.get("duration_seconds", 0) or 0)
        timestamp = offsets[segment] + starts_by_segment[segment][shot_id] + max(0.25, duration / 2)
        frame_path = FRAMES_DIR / segment / f"{shot_id}_v02_master_mid.png"
        extract_frame(master_video, timestamp, frame_path)
        metrics = image_metrics(frame_path)
        replacement = shot.get("replacement")
        reviewed.append(
            {
                "task_id": task_id,
                "segment": segment,
                "shot_id": shot_id,
                "label": item["label"],
                "timestamp_seconds": round(timestamp, 3),
                "duration_seconds": duration,
                "frame": rel(frame_path),
                "metrics": metrics,
                "replacement_provider": replacement.get("provider", "") if replacement else "",
                "replacement_review_frame": replacement.get("review_frame", "") if replacement else "",
                "review_focus": item["review_focus"],
                "risk_rules": item["risk_rules"],
                "director_status": "visual_evidence_ready" if metrics["nonblank"] else "frame_needs_repair",
                "risk_status": "rules_attached_pending_human_review",
            }
        )
    return reviewed


def contact_sheet(items: list[dict]) -> str:
    thumb_w, thumb_h = 384, 216
    label_h = 64
    columns = 2
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), (18, 20, 22))
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(items):
        x = (index % columns) * thumb_w
        y = (index // columns) * (thumb_h + label_h)
        frame_path = WORKSPACE / item["frame"]
        with Image.open(frame_path) as frame:
            thumb = frame.convert("RGB").resize((thumb_w, thumb_h))
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill=(28, 31, 34))
        draw.text((x + 12, y + thumb_h + 10), f"{item['shot_id']} | {item['label']}", fill=(240, 240, 235))
        draw.text(
            (x + 12, y + thumb_h + 34),
            f"t={item['timestamp_seconds']}s | nonblank={item['metrics']['nonblank']}",
            fill=(182, 190, 198),
        )
    output = FRAMES_DIR / "v02_master_review_contact_sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return rel(output)


def build_report(manifest: dict) -> str:
    lines = [
        "# Director And Risk Review Package v02",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Contact sheet: {manifest['contact_sheet']}",
        "",
        "## Summary",
        "",
        f"- Keyframes reviewed: {manifest['reviewed_keyframe_count']}",
        f"- Nonblank keyframes: {manifest['nonblank_keyframe_count']}",
        f"- Local-polish replacement shots in review set: {manifest['replacement_keyframe_count']}",
        f"- Risk shots in review set: {manifest['risk_keyframe_count']}",
        "",
        "## Keyframes",
        "",
        "| Shot | Segment | Time | Nonblank | Focus | Frame |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for item in manifest["keyframes"]:
        lines.append(
            f"| {item['shot_id']} | {item['segment']} | {item['timestamp_seconds']}s | "
            f"{item['metrics']['nonblank']} | {item['review_focus']} | {item['frame']} |"
        )
    lines.extend(
        [
            "",
            "## Director Notes",
            "",
            "- v02 is conditionally passable as the current local-polish producer demo candidate because the promoted master is complete and all selected evidence frames are nonblank.",
            "- The promoted local-polish shots are workflow/product-demo approvals only; final character consistency and art direction still need human review.",
            "- The next upgrade should replace local-polish clips with configured external provider outputs or a stronger manual polish pass.",
            "",
            "## Risk Notes",
            "",
            "- Risk-restricted shots are present with rules attached for human review.",
            "- This package does not certify final rating compliance or final originality clearance.",
            "- Commercial provider submission remains gated by credentials, cost cap, and producer approval.",
        ]
    )
    return "\n".join(lines)


def run_review(task_id: str) -> dict:
    master_manifest = load_json(MASTER_MANIFEST_PATH, {})
    demo_v02 = load_json(PRODUCER_DEMO_V02_PATH, {})
    master_video = resolve_project_path(master_manifest.get("video"))
    if not master_video or not master_video.exists():
        raise FileNotFoundError(master_manifest.get("video", "v02 master video"))

    segment_manifests = {segment: load_segment_manifest(segment) for segment in SEGMENTS}
    keyframes = review_keyframes(task_id, master_video, segment_manifests)
    sheet = contact_sheet(keyframes)
    nonblank_count = sum(1 for item in keyframes if item["metrics"]["nonblank"])
    replacement_count = sum(1 for item in keyframes if item.get("replacement_provider"))
    risk_count = sum(1 for item in keyframes if item.get("risk_rules"))
    package_ready = demo_v02.get("decision") == "packaged_for_local_polish_producer_demo"
    all_visual_evidence_ready = nonblank_count == len(keyframes)
    decision = (
        "conditional_pass_for_local_polish_producer_demo_v02"
        if package_ready and all_visual_evidence_ready
        else "return_v02_for_visual_or_package_repair"
    )
    manifest = {
        "task_id": task_id,
        "stage": "director_risk_review_v02",
        "source_producer_demo_v02": rel(PRODUCER_DEMO_V02_PATH) if PRODUCER_DEMO_V02_PATH.exists() else "",
        "source_master_manifest": rel(MASTER_MANIFEST_PATH) if MASTER_MANIFEST_PATH.exists() else "",
        "master_video": rel(master_video),
        "decision": decision,
        "final_release_ready": False,
        "reviewed_keyframe_count": len(keyframes),
        "nonblank_keyframe_count": nonblank_count,
        "replacement_keyframe_count": replacement_count,
        "risk_keyframe_count": risk_count,
        "contact_sheet": sheet,
        "keyframes": keyframes,
        "report": rel(REVIEW_DIR / "director_risk_review_v02.md"),
        "next_step": "Promote v02 as the current internal producer demo or route selected shots to configured external providers for a higher-quality pass.",
    }
    write_json(REVIEW_DIR / "director_risk_review_v02_manifest.json", manifest)
    (REVIEW_DIR / "director_risk_review_v02.md").write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-DIRECTOR-RISK-REVIEW-V02")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_review(args.task_id)
    output = REVIEW_DIR / "director_risk_review_v02_manifest.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
