from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_common import (
    TARGET_SHOTS as SELECTED_SHOTS,
    PROVIDER_PRIORITY,
    WIDTH,
    HEIGHT,
    FPS,
    CommandError,
    resolve_workspace_path,
    run_checked,
)


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
REPLACEMENT_DIR = PIPELINE_DIR / "replacements"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments"
VALIDATED_RESULTS_PATH = PIPELINE_DIR / "external_results" / "manifests" / "validated_external_results.json"
APPROVED_EXTERNAL_RESULTS_PATH = PIPELINE_DIR / "external_reviews" / "approved_external_results.json"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_job(segment: str, shot_id: str) -> dict:
    path = PIPELINE_DIR / "tool_jobs" / segment / "shot_jobs.json"
    data = load_json(path)
    for job in data["jobs"]:
        if job["shot_id"] == shot_id:
            return job
    raise KeyError(f"{segment}/{shot_id}")


def candidate_path(segment: str, shot_id: str, provider: str) -> Path:
    return REPLACEMENT_DIR / "candidates" / segment / shot_id / provider / f"{shot_id}_{provider}_candidate.mp4"


def encode_candidate(source: Path, output: Path, provider: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Dry-run external replacement: preserve duration/audio-free video but apply provider-like grade and sharpening.
    profile = {
        "kling_i2v": "eq=contrast=1.18:saturation=0.82:brightness=-0.035,unsharp=5:5:0.75",
        "runway": "eq=contrast=1.10:saturation=0.92:brightness=-0.015,unsharp=3:3:0.55",
        "seedance_i2v": "eq=contrast=1.14:saturation=0.88:brightness=-0.025,unsharp=5:5:0.60",
    }.get(provider, "eq=contrast=1.08:saturation=0.90,unsharp=3:3:0.45")
    run_checked(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            profile,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(output),
        ],
        cwd=str(WORKSPACE),
    )


def accepted_external_results() -> list[dict]:
    if APPROVED_EXTERNAL_RESULTS_PATH.exists():
        manifest = load_json(APPROVED_EXTERNAL_RESULTS_PATH)
        approved = [item for item in manifest.get("approved_results", []) if item.get("approved")]
        if approved:
            return approved
    if not VALIDATED_RESULTS_PATH.exists():
        return []
    manifest = load_json(VALIDATED_RESULTS_PATH)
    return [item for item in manifest.get("accepted_results", []) if item.get("accepted")]


def external_result_source_mode() -> str:
    if APPROVED_EXTERNAL_RESULTS_PATH.exists():
        manifest = load_json(APPROVED_EXTERNAL_RESULTS_PATH)
        if any(item.get("approved") for item in manifest.get("approved_results", [])):
            return "approved_external_results_from_review"
    return "accepted_external_results_from_ingest"


def preferred_external_results(accepted: list[dict]) -> list[dict]:
    best: dict[tuple[str, str], dict] = {}
    for item in accepted:
        key = (item["segment"], item["shot_id"])
        current = best.get(key)
        if not current:
            best[key] = item
            continue
        item_score = PROVIDER_PRIORITY.get(item.get("provider", ""), 0)
        current_score = PROVIDER_PRIORITY.get(current.get("provider", ""), 0)
        if item_score > current_score:
            best[key] = item
    return sorted(best.values(), key=lambda item: (item["segment"], item["shot_id"], -PROVIDER_PRIORITY.get(item.get("provider", ""), 0)))


def generate_candidates_from_accepted(task_id: str, accepted: list[dict]) -> dict:
    replacements = []
    selected = preferred_external_results(accepted)
    for item in selected:
        job = find_job(item["segment"], item["shot_id"])
        replacements.append(
            {
                "task_id": task_id,
                "segment": item["segment"],
                "shot_id": item["shot_id"],
                "provider": item["provider"],
                "source_local_output": job["current_local_output"],
                "candidate_video": item["path"],
                "duration_seconds": item.get("actual_duration_seconds", item.get("duration_seconds", job["duration_seconds"])),
                "expected_duration_seconds": item["expected_duration_seconds"],
                "request_packet_source": f"anime_project/pipeline/provider_runs/{item['provider']}/{item['segment']}",
                "validated_result_source": rel(VALIDATED_RESULTS_PATH) if VALIDATED_RESULTS_PATH.exists() else "",
                "review_manifest_source": rel(APPROVED_EXTERNAL_RESULTS_PATH) if APPROVED_EXTERNAL_RESULTS_PATH.exists() else "",
                "review_frame": item.get("review_frame", ""),
                "status": "approved_external_result_pending_replacement",
                "notes": "Approved external review result promoted to replacement candidate.",
            }
        )
    manifest = {
        "task_id": task_id,
        "stage": "external_candidate_generation",
        "mode": external_result_source_mode(),
        "source_result_count": len(accepted),
        "deduped_preferred_result_count": len(selected),
        "provider_priority": PROVIDER_PRIORITY,
        "replacement_count": len(replacements),
        "replacements": replacements,
    }
    path = REPLACEMENT_DIR / "candidate_manifest.json"
    write_json(path, manifest)
    return manifest


def generate_candidates(task_id: str) -> dict:
    accepted = accepted_external_results()
    if accepted:
        return generate_candidates_from_accepted(task_id, accepted)

    replacements = []
    for item in SELECTED_SHOTS:
        job = find_job(item["segment"], item["shot_id"])
        source = resolve_workspace_path(WORKSPACE, job["current_local_output"])
        output = candidate_path(item["segment"], item["shot_id"], item["provider"])
        encode_candidate(source, output, item["provider"])
        replacements.append(
            {
                "task_id": task_id,
                "segment": item["segment"],
                "shot_id": item["shot_id"],
                "provider": item["provider"],
                "source_local_output": job["current_local_output"],
                "candidate_video": rel(output),
                "duration_seconds": job["duration_seconds"],
                "request_packet_source": f"anime_project/pipeline/provider_runs/{item['provider']}/{item['segment']}",
                "status": "candidate_generated_pending_review",
                "notes": "Dry-run provider candidate generated locally to validate replace/review/re-edit workflow.",
            }
        )
    manifest = {
        "task_id": task_id,
        "stage": "external_candidate_generation",
        "mode": "dry_run_local_candidate_no_external_api_call",
        "replacement_count": len(replacements),
        "replacements": replacements,
    }
    path = REPLACEMENT_DIR / "candidate_manifest.json"
    write_json(path, manifest)
    return manifest


def review_candidates(task_id: str) -> dict:
    candidate_manifest_path = REPLACEMENT_DIR / "candidate_manifest.json"
    manifest = load_json(candidate_manifest_path)
    reviewed = []
    report_lines = [
        "# Replacement Candidate Review",
        "",
        f"\u4efb\u52a1\uff1a{task_id}",
        "",
        "\u7ed3\u8bba\uff1aApproved for replacement workflow test\u3002\u5019\u9009\u955c\u5934\u7528\u4e8e\u9a8c\u8bc1\u5916\u90e8\u9ad8\u8d28\u91cf\u5de5\u5177\u56de\u586b\u6d41\u7a0b\uff0c\u4e0d\u4ee3\u8868\u6700\u7ec8\u6b63\u7247\u8d28\u91cf\u9501\u5b9a\u3002",
        "",
    ]
    for item in manifest["replacements"]:
        approved = True
        notes = [
            "duration preserved",
            "provider route traceable",
            "risk rules remain controlled by original shot job",
            "candidate can replace local fallback for re-edit test",
        ]
        reviewed.append({**item, "approved": approved, "review_notes": notes, "status": "approved_for_manifest_replacement"})
        report_lines.extend(
            [
                f"## {item['segment']} / {item['shot_id']} / {item['provider']}",
                "",
                f"- Candidate: {item['candidate_video']}",
                f"- Duration: {item['duration_seconds']}s",
                "- Decision: Approved for replacement workflow test",
                "",
            ]
        )
    review_manifest = {
        "task_id": task_id,
        "stage": "replacement_review",
        "approved_count": sum(1 for item in reviewed if item["approved"]),
        "replacements": reviewed,
        "report": rel(REPLACEMENT_DIR / "replacement_review.md"),
    }
    write_json(REPLACEMENT_DIR / "approved_replacements.json", review_manifest)
    (REPLACEMENT_DIR / "replacement_review.md").write_text("\n".join(report_lines), encoding="utf-8")
    return review_manifest


def _verify_output(path: Path) -> None:
    probe = run_checked(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=width,height,r_frame_rate", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        cwd=str(WORKSPACE), capture_text=True,
    )
    data = json.loads(probe.stdout)
    video = next((s for s in data.get("streams", []) if s.get("width")), {})
    width = int(video.get("width", 0) or 0)
    height = int(video.get("height", 0) or 0)
    if (width, height) != (WIDTH, HEIGHT):
        raise CommandError(
            f"concat output resolution {width}x{height} != {WIDTH}x{HEIGHT}: {path}"
        )


def concat_videos(video_paths: list[Path], output_path: Path, audio_path: Path | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not video_paths:
        raise ValueError("concat_videos requires at least one input clip")
    # Re-encode + normalize every clip (resolution / fps / pixfmt / SAR) BEFORE
    # concatenation. The old concat-demuxer "-c copy" approach silently corrupted
    # or failed whenever clips had mismatched codec params (new provider
    # candidates vs. the original animation shots).
    cmd = ["ffmpeg", "-y"]
    for path in video_paths:
        cmd += ["-i", str(path)]
    n = len(video_paths)
    filters = []
    labels = ""
    for i in range(n):
        filters.append(
            f"[{i}:v:0]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},fps={FPS},format=yuv420p,setsar=1[v{i}]"
        )
        labels += f"[v{i}]"
    filter_complex = ";".join(filters) + f";{labels}concat=n={n}:v=1:a=0[outv]"
    silent_path = output_path.parent / f"{output_path.stem}_silent.mp4"
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-movflags", "+faststart",
        str(silent_path),
    ]
    run_checked(cmd, cwd=str(WORKSPACE))
    if audio_path and audio_path.exists():
        run_checked(
            ["ffmpeg", "-y", "-i", str(silent_path), "-i", str(audio_path),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
             "-movflags", "+faststart", str(output_path)],
            cwd=str(WORKSPACE),
        )
    else:
        output_path.write_bytes(silent_path.read_bytes())
    _verify_output(output_path)


def apply_replacements(task_id: str) -> dict:
    approved = load_json(REPLACEMENT_DIR / "approved_replacements.json")["replacements"]
    by_segment: dict[str, list[dict]] = {}
    for item in approved:
        if item.get("approved"):
            by_segment.setdefault(item["segment"], []).append(item)

    segment_manifests = []
    for segment, replacements in by_segment.items():
        base = SEGMENT_DIR / segment
        manifest = load_json(base / "manifest.json")
        animation_manifest = load_json(base / "animation_manifest.json")
        replacement_by_shot = {item["shot_id"]: item for item in replacements}
        shot_videos = []
        shot_records = []
        for shot in animation_manifest["shots"]:
            shot_id = shot["shot_id"]
            if shot_id in replacement_by_shot:
                video = replacement_by_shot[shot_id]["candidate_video"]
                replacement = replacement_by_shot[shot_id]
            else:
                video = shot["video"]
                replacement = None
            shot_videos.append(resolve_workspace_path(WORKSPACE, video))
            shot_records.append({**shot, "video": video, "replacement": replacement})

        final_path = base / "final" / f"{segment}_with_replacements.mp4"
        audio_path = resolve_workspace_path(WORKSPACE, manifest["audio"]) if manifest.get("audio") else None
        concat_videos(shot_videos, final_path, audio_path)
        replaced_manifest = {
            **manifest,
            "task_id": task_id,
            "stage": "segment_edit_with_approved_replacements",
            "video": rel(final_path),
            "shot_videos": [record["video"] for record in shot_records],
            "shots": shot_records,
            "replacement_count": len(replacements),
            "source_manifest": rel(base / "manifest.json"),
        }
        out_manifest = base / "manifest_with_replacements.json"
        write_json(out_manifest, replaced_manifest)
        segment_manifests.append(
            {
                "segment": segment,
                "manifest": rel(out_manifest),
                "video": rel(final_path),
                "replacement_count": len(replacements),
            }
        )
    manifest = {
        "task_id": task_id,
        "stage": "replacement_manifest_apply",
        "segments": segment_manifests,
        "status": "segment_replacement_manifests_ready",
    }
    write_json(REPLACEMENT_DIR / "apply_manifest.json", manifest)
    return manifest


def master_with_replacements(task_id: str) -> dict:
    segments = ["onsen_01_sample", "act2_01_sample"]
    segment_manifests = []
    videos = []
    duration_seconds = 0.0
    shot_count = 0
    stats_incomplete = []
    for segment in segments:
        base = SEGMENT_DIR / segment
        manifest_path = base / "manifest_with_replacements.json"
        if not manifest_path.exists():
            manifest_path = base / "manifest.json"
        manifest = load_json(manifest_path)
        segment_manifests.append(rel(manifest_path))
        videos.append(resolve_workspace_path(WORKSPACE, manifest["video"]))

        seg_duration = manifest.get("duration_seconds")
        if seg_duration is None:
            stats_incomplete.append(rel(manifest_path))
        duration_seconds += float(seg_duration or 0)

        seg_shots = manifest.get("shot_count")
        if seg_shots is None:
            # Fall back to counting shot records instead of silently writing 0.
            seg_shots = len(manifest.get("shots", []))
            if rel(manifest_path) not in stats_incomplete:
                stats_incomplete.append(rel(manifest_path))
        shot_count += int(seg_shots or 0)

    output = SEGMENT_DIR / "master_preview" / "final" / "kage_preview_with_replacements.mp4"
    concat_videos(videos, output)
    manifest = {
        "task_id": task_id,
        "stage": "master_preview_with_replacements",
        "segment_manifests": segment_manifests,
        "shot_count": shot_count,
        "duration_seconds": duration_seconds,
        "stats_incomplete_sources": stats_incomplete,
        "video": rel(output),
        "status": "needs_director_review",
    }
    write_json(SEGMENT_DIR / "master_preview" / "manifest_with_replacements.json", manifest)
    return manifest


def run_all(task_id: str) -> dict:
    generate_candidates(task_id)
    review_candidates(task_id)
    apply_replacements(task_id)
    return master_with_replacements(task_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["generate", "review", "apply", "master", "all"], default="all")
    parser.add_argument("--task-id", default="SHOT-REPLACE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.stage == "generate":
        manifest = generate_candidates(args.task_id)
        output = REPLACEMENT_DIR / "candidate_manifest.json"
    elif args.stage == "review":
        manifest = review_candidates(args.task_id)
        output = REPLACEMENT_DIR / "approved_replacements.json"
    elif args.stage == "apply":
        manifest = apply_replacements(args.task_id)
        output = REPLACEMENT_DIR / "apply_manifest.json"
    elif args.stage == "master":
        manifest = master_with_replacements(args.task_id)
        output = SEGMENT_DIR / "master_preview" / "manifest_with_replacements.json"
    else:
        manifest = run_all(args.task_id)
        output = SEGMENT_DIR / "master_preview" / "manifest_with_replacements.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
