from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
ACCEPTANCE_DIR = PIPELINE_DIR / "acceptance"

MASTER_MANIFEST = SEGMENT_DIR / "master_preview" / "manifest_with_replacements.json"
SEGMENTS = ["onsen_01_sample", "act2_01_sample"]


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


def file_status(raw_path: str | None) -> dict:
    path = resolve_project_path(raw_path)
    exists = bool(path and path.exists())
    return {
        "path": raw_path or "",
        "exists": exists,
        "bytes": path.stat().st_size if exists and path and path.is_file() else 0,
    }


def ffprobe_media(raw_path: str | None) -> dict:
    path = resolve_project_path(raw_path)
    if not path or not path.exists():
        return {"exists": False, "streams": [], "format_duration_seconds": 0.0}
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration",
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
    return {
        "exists": True,
        "streams": data.get("streams", []),
        "format_duration_seconds": float(data.get("format", {}).get("duration") or 0),
    }


def fps_value(raw_fps: str) -> float:
    if not raw_fps or raw_fps == "0/0":
        return 0.0
    if "/" not in raw_fps:
        return float(raw_fps)
    numerator, denominator = raw_fps.split("/", 1)
    return float(numerator) / float(denominator or 1)


def summarize_segment(segment: str) -> dict:
    manifest_path = SEGMENT_DIR / segment / "manifest_with_replacements.json"
    if not manifest_path.exists():
        manifest_path = SEGMENT_DIR / segment / "manifest.json"
    manifest = load_json(manifest_path, {})
    shots = manifest.get("shots", [])
    shot_videos = manifest.get("shot_videos", [])
    missing_shots = [video for video in shot_videos if not file_status(video)["exists"]]
    replacement_count = manifest.get("replacement_count", 0)
    if not replacement_count:
        replacement_count = sum(1 for shot in shots if shot.get("replacement"))
    return {
        "segment": segment,
        "manifest": rel(manifest_path) if manifest_path.exists() else "",
        "video": file_status(manifest.get("video")),
        "audio": file_status(manifest.get("audio")),
        "shot_count": manifest.get("shot_count", len(shot_videos)),
        "shot_video_count": len(shot_videos),
        "missing_shot_count": len(missing_shots),
        "missing_shots": missing_shots,
        "replacement_count": replacement_count,
        "duration_seconds": manifest.get("duration_seconds", 0),
        "width": manifest.get("width", 0),
        "height": manifest.get("height", 0),
        "fps": manifest.get("fps", 0),
        "review_status": manifest.get("review_status", ""),
    }


def risk_rule_check(segment_summaries: list[dict]) -> dict:
    act2_manifest = load_json(SEGMENT_DIR / "act2_01_sample" / "manifest_with_replacements.json", {})
    shot_ids = {shot.get("shot_id") for shot in act2_manifest.get("shots", [])}
    required = ["08-003", "11-004", "12-001", "12-002", "12-003"]
    return {
        "status": "rule_markers_present" if all(shot_id in shot_ids for shot_id in required) else "needs_manual_trace",
        "rules": [
            "08-003: no face or pain expression.",
            "11-004: parasite count limit is 8.",
            "12-001 to 12-003: no child pain process; use props, hands, and silence.",
        ],
        "required_shots_present": {shot_id: shot_id in shot_ids for shot_id in required},
        "note": "Machine check verifies shot IDs and attached production rules; DirectorAgent/RiskAgent still need visual review.",
    }


def checklist(master_manifest: dict, master_probe: dict, segments: list[dict]) -> dict:
    video_streams = [stream for stream in master_probe.get("streams", []) if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in master_probe.get("streams", []) if stream.get("codec_type") == "audio"]
    video = video_streams[0] if video_streams else {}
    replacements = load_json(PIPELINE_DIR / "replacements" / "candidate_manifest.json", {})
    external_review = load_json(PIPELINE_DIR / "external_reviews" / "approved_external_results.json", {})
    submit_gate = load_json(PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json", {})
    provider_submit = load_json(PIPELINE_DIR / "submit_runs" / "external_video" / "submit_run_manifest.json", {})

    video_format_pass = (
        master_probe.get("exists")
        and video.get("codec_name") == "h264"
        and video.get("width") == 1920
        and video.get("height") == 1080
        and abs(fps_value(video.get("avg_frame_rate", "")) - 24) < 0.01
        and bool(audio_streams)
    )
    segment_completeness_pass = all(
        segment["video"]["exists"]
        and segment["audio"]["exists"]
        and segment["missing_shot_count"] == 0
        and segment["shot_count"] == segment["shot_video_count"]
        for segment in segments
    )
    replacement_traceability_pass = (
        replacements.get("mode") == "approved_external_results_from_review"
        and replacements.get("replacement_count", 0) == external_review.get("approved_count", 0)
        and external_review.get("approved_count", 0) >= 2
    )
    external_review_gate_pass = (
        external_review.get("reviewed_count", 0) == external_review.get("approved_count", 0)
        and external_review.get("approved_count", 0) >= 2
    )
    submit_safety_pass = (
        submit_gate.get("allowed_provider_count", 0) == 0
        and submit_gate.get("blocked_provider_count", 0) >= 5
        and provider_submit.get("submitted_count", 0) == 0
    )
    master_continuity_pass = (
        master_manifest.get("shot_count") == sum(segment["shot_count"] for segment in segments)
        and abs(float(master_manifest.get("duration_seconds", 0)) - sum(float(segment["duration_seconds"]) for segment in segments))
        <= 0.25
    )
    passes = {
        "video_format_pass": bool(video_format_pass),
        "segment_completeness_pass": bool(segment_completeness_pass),
        "master_continuity_pass": bool(master_continuity_pass),
        "external_review_gate_pass": bool(external_review_gate_pass),
        "replacement_traceability_pass": bool(replacement_traceability_pass),
        "submit_safety_pass": bool(submit_safety_pass),
    }
    return {
        "checks": passes,
        "passed_count": sum(1 for passed in passes.values() if passed),
        "failed_count": sum(1 for passed in passes.values() if not passed),
    }


def build_report(manifest: dict) -> str:
    checks = manifest["checklist"]["checks"]
    lines = [
        "# Master Acceptance Report",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        "",
        "## Master",
        "",
        f"- Video: {manifest['master']['video']['path']}",
        f"- Format: {manifest['master']['width']}x{manifest['master']['height']} / {manifest['master']['fps']}fps / H.264 MP4",
        f"- Duration: {manifest['master']['duration_seconds']}s manifest, {manifest['master']['ffprobe_duration_seconds']:.3f}s ffprobe",
        f"- Streams: video={manifest['master']['has_video']}, audio={manifest['master']['has_audio']}",
        "",
        "## Checklist",
        "",
    ]
    for name, passed in checks.items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} {name}")
    lines.extend(
        [
            "",
            "## Segments",
            "",
            "| Segment | Shots | Missing | Duration | Replacements |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for segment in manifest["segments"]:
        lines.append(
            f"| {segment['segment']} | {segment['shot_count']} | {segment['missing_shot_count']} | "
            f"{segment['duration_seconds']}s | {segment['replacement_count']} |"
        )
    lines.extend(
        [
            "",
            "## External Flow",
            "",
            f"- Reviewed external results: {manifest['external_reviews']['reviewed_count']}",
            f"- Approved external results: {manifest['external_reviews']['approved_count']}",
            f"- Replacement source mode: {manifest['replacements']['mode']}",
            f"- Commercial submits: {manifest['provider_submit']['submitted_count']} submitted; "
            f"{manifest['submit_gate']['blocked_provider_count']} providers blocked by gate.",
            "",
            "## Release Note",
            "",
            "This is ready for internal director/producer review as a product prototype sample. "
            "It is not marked final-release-ready until human visual, rating, originality, and sound reviews are completed.",
        ]
    )
    return "\n".join(lines)


def run_acceptance(task_id: str) -> dict:
    master_manifest = load_json(MASTER_MANIFEST, {})
    master_video = master_manifest.get("video")
    master_probe = ffprobe_media(master_video)
    video_streams = [stream for stream in master_probe.get("streams", []) if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in master_probe.get("streams", []) if stream.get("codec_type") == "audio"]
    video = video_streams[0] if video_streams else {}
    segment_summaries = [summarize_segment(segment) for segment in SEGMENTS]
    checklist_summary = checklist(master_manifest, master_probe, segment_summaries)
    external_review = load_json(PIPELINE_DIR / "external_reviews" / "approved_external_results.json", {})
    replacements = load_json(PIPELINE_DIR / "replacements" / "candidate_manifest.json", {})
    submit_gate = load_json(PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json", {})
    provider_submit = load_json(PIPELINE_DIR / "submit_runs" / "external_video" / "submit_run_manifest.json", {})
    all_machine_checks_pass = checklist_summary["failed_count"] == 0

    manifest = {
        "task_id": task_id,
        "stage": "master_acceptance",
        "decision": "ready_for_director_producer_review" if all_machine_checks_pass else "needs_machine_fix",
        "final_release_ready": False,
        "master": {
            "manifest": rel(MASTER_MANIFEST) if MASTER_MANIFEST.exists() else "",
            "video": file_status(master_video),
            "shot_count": master_manifest.get("shot_count", 0),
            "duration_seconds": float(master_manifest.get("duration_seconds", 0)),
            "ffprobe_duration_seconds": master_probe.get("format_duration_seconds", 0.0),
            "width": video.get("width", 0),
            "height": video.get("height", 0),
            "fps": fps_value(video.get("avg_frame_rate", "")),
            "video_codec": video.get("codec_name", ""),
            "has_video": bool(video_streams),
            "has_audio": bool(audio_streams),
            "audio_codec": audio_streams[0].get("codec_name", "") if audio_streams else "",
            "status": master_manifest.get("status", ""),
        },
        "segments": segment_summaries,
        "checklist": checklist_summary,
        "risk_rules": risk_rule_check(segment_summaries),
        "external_reviews": {
            "manifest": rel(PIPELINE_DIR / "external_reviews" / "approved_external_results.json")
            if (PIPELINE_DIR / "external_reviews" / "approved_external_results.json").exists()
            else "",
            "reviewed_count": external_review.get("reviewed_count", 0),
            "approved_count": external_review.get("approved_count", 0),
            "returned_count": external_review.get("returned_count", 0),
            "report": external_review.get("report", ""),
        },
        "replacements": {
            "manifest": rel(PIPELINE_DIR / "replacements" / "candidate_manifest.json")
            if (PIPELINE_DIR / "replacements" / "candidate_manifest.json").exists()
            else "",
            "mode": replacements.get("mode", ""),
            "replacement_count": replacements.get("replacement_count", 0),
            "items": replacements.get("replacements", []),
        },
        "submit_gate": {
            "manifest": rel(PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json")
            if (PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json").exists()
            else "",
            "allowed_provider_count": submit_gate.get("allowed_provider_count", 0),
            "blocked_provider_count": submit_gate.get("blocked_provider_count", 0),
            "total_estimated_cost_usd": submit_gate.get("total_estimated_cost_usd", 0),
            "approval_request": submit_gate.get("approval_request", ""),
        },
        "provider_submit": {
            "manifest": rel(PIPELINE_DIR / "submit_runs" / "external_video" / "submit_run_manifest.json")
            if (PIPELINE_DIR / "submit_runs" / "external_video" / "submit_run_manifest.json").exists()
            else "",
            "submitted_count": provider_submit.get("submitted_count", 0),
            "blocked_provider_count": provider_submit.get("blocked_provider_count", 0),
            "failed_count": provider_submit.get("failed_count", 0),
        },
        "report": rel(ACCEPTANCE_DIR / "master_acceptance_report.md"),
        "next_step": "DirectorAgent and RiskAgent should do human visual review before finance-facing release.",
    }
    write_json(ACCEPTANCE_DIR / "master_acceptance_manifest.json", manifest)
    (ACCEPTANCE_DIR / "master_acceptance_report.md").write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-MASTER-ACCEPTANCE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_acceptance(args.task_id)
    output = ACCEPTANCE_DIR / "master_acceptance_manifest.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
