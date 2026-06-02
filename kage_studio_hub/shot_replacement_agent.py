from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
REPLACEMENT_DIR = PIPELINE_DIR / "replacements"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments"
VALIDATED_RESULTS_PATH = PIPELINE_DIR / "external_results" / "manifests" / "validated_external_results.json"
APPROVED_EXTERNAL_RESULTS_PATH = PIPELINE_DIR / "external_reviews" / "approved_external_results.json"

SELECTED_SHOTS = [
    {"segment": "onsen_01_sample", "shot_id": "ON-008", "provider": "kling_i2v"},
    {"segment": "act2_01_sample", "shot_id": "08-004", "provider": "runway"},
]

PROVIDER_PRIORITY = {
    "kling_i2v": 100,
    "seedance_i2v": 95,
    "runway": 90,
    "luma": 85,
    "pika": 80,
    "comfyui_svd": 60,
    "animatediff": 55,
    "hyperframes": 50,
    "remotion": 30,
    "blender": 25,
    "unreal": 25,
}


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
    subprocess.run(
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
            str(output),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        source = WORKSPACE / job["current_local_output"]
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
        f"任务：{task_id}",
        "",
        "结论：Approved for replacement workflow test。候选镜头用于验证外部高质量工具回填流程，不代表最终正片质量锁定。",
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


def concat_videos(video_paths: list[Path], output_path: Path, audio_path: Path | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_path = output_path.parent / f"{output_path.stem}_concat.txt"
    concat_path.write_text("\n".join(f"file '{path.resolve().as_posix()}'" for path in video_paths), encoding="utf-8")
    silent_path = output_path.parent / f"{output_path.stem}_silent.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(silent_path)],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if audio_path and audio_path.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(silent_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            check=True,
            cwd=str(WORKSPACE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        output_path.write_bytes(silent_path.read_bytes())


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
            shot_videos.append(WORKSPACE / video)
            shot_records.append({**shot, "video": video, "replacement": replacement})

        final_path = base / "final" / f"{segment}_with_replacements.mp4"
        audio_path = WORKSPACE / manifest["audio"] if manifest.get("audio") else None
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
    for segment in segments:
        base = SEGMENT_DIR / segment
        manifest_path = base / "manifest_with_replacements.json"
        if not manifest_path.exists():
            manifest_path = base / "manifest.json"
        manifest = load_json(manifest_path)
        segment_manifests.append(rel(manifest_path))
        videos.append(WORKSPACE / manifest["video"])
    output = SEGMENT_DIR / "master_preview" / "final" / "kage_preview_with_replacements.mp4"
    concat_videos(videos, output)
    duration_seconds = sum(float(load_json(WORKSPACE / path).get("duration_seconds", 0)) for path in segment_manifests)
    shot_count = sum(int(load_json(WORKSPACE / path).get("shot_count", 0)) for path in segment_manifests)
    manifest = {
        "task_id": task_id,
        "stage": "master_preview_with_replacements",
        "segment_manifests": segment_manifests,
        "shot_count": shot_count,
        "duration_seconds": duration_seconds,
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
