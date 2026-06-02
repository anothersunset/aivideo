from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments"
PROMOTION_DIR = PIPELINE_DIR / "polish_outputs" / "local_remotion" / "promotion"
LOCAL_POLISH_MANIFEST = PIPELINE_DIR / "polish_outputs" / "local_remotion" / "local_polish_render_manifest.json"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def accepted_local_polish(task_id: str) -> list[dict]:
    manifest = load_json(LOCAL_POLISH_MANIFEST)
    accepted = []
    for item in manifest.get("renders", []):
        if not item.get("accepted"):
            continue
        accepted.append(
            {
                "task_id": task_id,
                "queue_id": item.get("queue_id", ""),
                "segment": item["segment"],
                "shot_id": item["shot_id"],
                "provider": "local_remotion_polish",
                "source_local_output": item.get("source_video", ""),
                "candidate_video": item["output"],
                "duration_seconds": item.get("duration_seconds", 0),
                "expected_duration_seconds": item.get("duration_seconds", 0),
                "review_frame": item.get("review_frame", ""),
                "local_polish_manifest_source": rel(LOCAL_POLISH_MANIFEST),
                "status": "approved_for_manifest_replacement",
                "notes": "Accepted local polish candidate promoted into versioned replacement edit.",
                "approved": True,
                "review_notes": [
                    "local polish render accepted",
                    "1920x1080 24fps h264 verification inherited from LocalPolishRenderAgent",
                    "risk rules remain controlled by original shot job and director review metadata",
                ],
            }
        )
    return accepted


def write_promotion_inputs(task_id: str, replacements: list[dict]) -> dict:
    manifest = {
        "task_id": task_id,
        "stage": "local_polish_replacement_promotion",
        "mode": "versioned_local_polish_master_no_external_api_call",
        "source_manifest": rel(LOCAL_POLISH_MANIFEST),
        "approved_count": len(replacements),
        "replacements": replacements,
        "next_step": "Use the local-polish master preview for director review or package it as the next producer demo version.",
    }
    write_json(PROMOTION_DIR / "approved_local_polish_replacements.json", manifest)
    return manifest


def apply_segment_polish(task_id: str, segment: str, replacements: list[dict]) -> dict:
    base = SEGMENT_DIR / segment
    manifest = load_json(base / "manifest.json")
    animation_manifest = load_json(base / "animation_manifest.json")
    replacement_by_shot = {item["shot_id"]: item for item in replacements}
    shot_videos = []
    shot_records = []
    for shot in animation_manifest["shots"]:
        shot_id = shot["shot_id"]
        replacement = replacement_by_shot.get(shot_id)
        video = replacement["candidate_video"] if replacement else shot["video"]
        shot_videos.append(WORKSPACE / video)
        shot_records.append({**shot, "video": video, "replacement": replacement})

    final_path = base / "final" / f"{segment}_with_local_polish.mp4"
    audio_path = WORKSPACE / manifest["audio"] if manifest.get("audio") else None
    concat_videos(shot_videos, final_path, audio_path)
    segment_manifest = {
        **manifest,
        "task_id": task_id,
        "stage": "segment_edit_with_local_polish_replacements",
        "video": rel(final_path),
        "shot_videos": [record["video"] for record in shot_records],
        "shots": shot_records,
        "replacement_count": len(replacements),
        "source_manifest": rel(base / "manifest.json"),
        "local_polish_source_manifest": rel(LOCAL_POLISH_MANIFEST),
    }
    out_manifest = base / "manifest_with_local_polish.json"
    write_json(out_manifest, segment_manifest)
    return {
        "segment": segment,
        "manifest": rel(out_manifest),
        "video": rel(final_path),
        "replacement_count": len(replacements),
    }


def master_with_local_polish(task_id: str, segment_manifests: list[dict]) -> dict:
    videos = []
    manifest_paths = []
    duration_seconds = 0.0
    shot_count = 0
    for item in segment_manifests:
        manifest_path = WORKSPACE / item["manifest"]
        manifest = load_json(manifest_path)
        manifest_paths.append(item["manifest"])
        videos.append(WORKSPACE / manifest["video"])
        duration_seconds += float(manifest.get("duration_seconds", 0))
        shot_count += int(manifest.get("shot_count", 0))

    output = SEGMENT_DIR / "master_preview" / "final" / "kage_preview_with_local_polish.mp4"
    concat_videos(videos, output)
    manifest = {
        "task_id": task_id,
        "stage": "master_preview_with_local_polish",
        "segment_manifests": manifest_paths,
        "shot_count": shot_count,
        "duration_seconds": duration_seconds,
        "video": rel(output),
        "status": "needs_director_review",
    }
    write_json(SEGMENT_DIR / "master_preview" / "manifest_with_local_polish.json", manifest)
    return manifest


def build_report(manifest: dict) -> str:
    lines = [
        "# Local Polish Promotion Report",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Promoted replacements: {manifest['promoted_count']}",
        f"Master video: {manifest['master_video']}",
        "",
        "## Segment Outputs",
        "",
        "| Segment | Replacements | Manifest | Video |",
        "| --- | ---: | --- | --- |",
    ]
    for item in manifest["segments"]:
        lines.append(f"| {item['segment']} | {item['replacement_count']} | {item['manifest']} | {item['video']} |")
    lines.extend(["", "## Promoted Shots", "", "| Segment | Shot | Queue | Candidate |", "| --- | --- | --- | --- |"])
    for item in manifest["replacements"]:
        lines.append(f"| {item['segment']} | {item['shot_id']} | {item['queue_id']} | {item['candidate_video']} |")
    lines.extend(["", "## Next Step", "", manifest["next_step"]])
    return "\n".join(lines)


def run_promotion(task_id: str) -> dict:
    replacements = accepted_local_polish(task_id)
    promotion_inputs = write_promotion_inputs(task_id, replacements)
    by_segment: dict[str, list[dict]] = {}
    for item in replacements:
        by_segment.setdefault(item["segment"], []).append(item)

    segment_outputs = []
    for segment in ["onsen_01_sample", "act2_01_sample"]:
        segment_outputs.append(apply_segment_polish(task_id, segment, by_segment.get(segment, [])))
    master = master_with_local_polish(task_id, segment_outputs)

    manifest = {
        "task_id": task_id,
        "stage": "local_polish_promotion",
        "mode": promotion_inputs["mode"],
        "decision": "local_polish_promoted_to_master_preview",
        "manifest": rel(PROMOTION_DIR / "local_polish_promotion_manifest.json"),
        "source_manifest": rel(LOCAL_POLISH_MANIFEST),
        "approved_replacements_manifest": rel(PROMOTION_DIR / "approved_local_polish_replacements.json"),
        "promoted_count": len(replacements),
        "segments": segment_outputs,
        "master_manifest": rel(SEGMENT_DIR / "master_preview" / "manifest_with_local_polish.json"),
        "master_video": master["video"],
        "replacements": replacements,
        "next_step": "Run director/risk review against the local-polish master or package it as producer_demo_v02.",
    }
    manifest["report"] = rel(PROMOTION_DIR / "local_polish_promotion_report.md")
    write_json(PROMOTION_DIR / "local_polish_promotion_manifest.json", manifest)
    (PROMOTION_DIR / "local_polish_promotion_report.md").write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="LOCAL-POLISH-PROMOTE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_promotion(args.task_id)
    if args.quiet:
        print(manifest["manifest"])
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
