from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
TOOL_JOBS_DIR = PIPELINE_DIR / "tool_jobs"
RESULT_DIR = PIPELINE_DIR / "external_results"
INBOX_DIR = RESULT_DIR / "inbox"
MANIFEST_DIR = RESULT_DIR / "manifests"
VIDEO_PROVIDERS = [
    "kling_i2v",
    "seedance_i2v",
    "runway",
    "luma",
    "pika",
    "comfyui_svd",
    "animatediff",
    "remotion",
    "hyperframes",
    "blender",
    "unreal",
]
SEGMENTS = ["onsen_01_sample", "act2_01_sample"]


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jobs(segment: str) -> list[dict]:
    path = TOOL_JOBS_DIR / segment / "shot_jobs.json"
    return load_json(path)["jobs"]


def build_expected_manifest() -> dict:
    expected = []
    for segment in SEGMENTS:
        for job in load_jobs(segment):
            for provider in VIDEO_PROVIDERS:
                drop_dir = INBOX_DIR / provider / segment / job["shot_id"]
                drop_dir.mkdir(parents=True, exist_ok=True)
                expected_name = f"{job['shot_id']}_{provider}.mp4"
                expected.append(
                    {
                        "provider": provider,
                        "segment": segment,
                        "shot_id": job["shot_id"],
                        "duration_seconds": job["duration_seconds"],
                        "expected_path": rel(drop_dir / expected_name),
                        "current_local_output": job["current_local_output"],
                        "status": "waiting_for_external_result",
                    }
                )
    manifest = {
        "stage": "external_result_dropbox",
        "mode": "no_external_api_call",
        "providers": VIDEO_PROVIDERS,
        "segments": SEGMENTS,
        "expected_result_count": len(expected),
        "inbox": rel(INBOX_DIR),
        "expected_results": expected,
    }
    write_json(MANIFEST_DIR / "expected_external_results.json", manifest)
    return manifest


def ffprobe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames",
            "-show_entries",
            "format=duration,size",
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
    return json.loads(result.stdout)


def index_jobs() -> dict[tuple[str, str], dict]:
    lookup = {}
    for segment in SEGMENTS:
        for job in load_jobs(segment):
            lookup[(segment, job["shot_id"])] = job
    return lookup


def parse_result_path(path: Path) -> tuple[str, str, str] | None:
    try:
        rel_parts = path.relative_to(INBOX_DIR).parts
    except ValueError:
        return None
    if len(rel_parts) < 4:
        return None
    provider, segment, shot_id = rel_parts[0], rel_parts[1], rel_parts[2]
    return provider, segment, shot_id


def validate_result(path: Path, job: dict, provider: str, segment: str, shot_id: str) -> dict:
    probe = ffprobe(path)
    streams = probe.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    fmt = probe.get("format", {})
    duration = float(fmt.get("duration", 0) or 0)
    target_duration = float(job.get("duration_seconds", 0) or 0)
    fps = video.get("r_frame_rate", "")
    width = int(video.get("width", 0) or 0)
    height = int(video.get("height", 0) or 0)
    checks = {
        "has_video": bool(video),
        "resolution_1920x1080": width == 1920 and height == 1080,
        "fps_24": fps == "24/1",
        "duration_close": abs(duration - target_duration) <= max(0.5, target_duration * 0.08),
        "non_empty": int(fmt.get("size", 0) or 0) > 100_000,
    }
    accepted = all(checks.values())
    return {
        "provider": provider,
        "segment": segment,
        "shot_id": shot_id,
        "path": rel(path),
        "expected_duration_seconds": target_duration,
        "actual_duration_seconds": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": video.get("codec_name", ""),
        "checks": checks,
        "accepted": accepted,
        "status": "accepted_for_review" if accepted else "rejected_needs_fix",
    }


def scan_inbox() -> dict:
    build_expected_manifest()
    lookup = index_jobs()
    accepted = []
    rejected = []
    unknown = []
    for path in INBOX_DIR.rglob("*.mp4"):
        parsed = parse_result_path(path)
        if not parsed:
            unknown.append({"path": rel(path), "reason": "path must be inbox/{provider}/{segment}/{shot_id}/file.mp4"})
            continue
        provider, segment, shot_id = parsed
        job = lookup.get((segment, shot_id))
        if provider not in VIDEO_PROVIDERS or not job:
            unknown.append({"path": rel(path), "provider": provider, "segment": segment, "shot_id": shot_id})
            continue
        try:
            result = validate_result(path, job, provider, segment, shot_id)
        except Exception as exc:  # noqa: BLE001
            rejected.append({"path": rel(path), "provider": provider, "segment": segment, "shot_id": shot_id, "error": str(exc)})
            continue
        if result["accepted"]:
            accepted.append(result)
        else:
            rejected.append(result)
    manifest = {
        "stage": "external_result_scan",
        "inbox": rel(INBOX_DIR),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "unknown_count": len(unknown),
        "accepted_results": accepted,
        "rejected_results": rejected,
        "unknown_results": unknown,
        "next_step": "Approved accepted_results can be reviewed, then converted into replacement manifests for segment re-edit.",
    }
    write_json(MANIFEST_DIR / "validated_external_results.json", manifest)
    write_readme()
    return manifest


def write_readme() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    readme = """# External Result Inbox

Drop externally generated MP4 files here using this path convention:

`inbox/{provider}/{segment}/{shot_id}/{shot_id}_{provider}.mp4`

Example:

`inbox/runway/onsen_01_sample/ON-008/ON-008_runway.mp4`

Validation rules:

- 1920x1080
- 24fps
- MP4 with video stream
- Duration close to the shot job duration
- File is non-empty

Accepted files are recorded in `manifests/validated_external_results.json`.
"""
    (RESULT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["prepare", "scan"], default="scan")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.mode == "prepare":
        manifest = build_expected_manifest()
        write_readme()
        output_path = MANIFEST_DIR / "expected_external_results.json"
    else:
        manifest = scan_inbox()
        output_path = MANIFEST_DIR / "validated_external_results.json"
    if args.quiet:
        print(rel(output_path))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
