from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
MASTER_DIR = ANIME_PROJECT / "episode_segments" / "master_preview"
FINAL_DIR = MASTER_DIR / "final"
SEGMENTS = ["onsen_01_sample", "act2_01_sample"]


def read_segment_manifest(segment: str) -> dict:
    path = ANIME_PROJECT / "episode_segments" / segment / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def concat_segments(manifests: list[dict], output_path: Path) -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    concat_path = MASTER_DIR / "concat_segments.txt"
    concat_path.write_text(
        "\n".join(f"file '{(WORKSPACE / item['video']).resolve().as_posix()}'" for item in manifests),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def render_master(task_id: str) -> dict:
    manifests = [read_segment_manifest(segment) for segment in SEGMENTS]
    output_path = FINAL_DIR / "kage_preview_onsen_plus_act2.mp4"
    concat_segments(manifests, output_path)
    manifest = {
        "task_id": task_id,
        "stage": "master_preview_edit",
        "segments": SEGMENTS,
        "segment_videos": [item["video"] for item in manifests],
        "shot_count": sum(item.get("shot_count", 0) for item in manifests),
        "duration_seconds": sum(float(item.get("duration_seconds", 0)) for item in manifests),
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "video": str(output_path.relative_to(WORKSPACE)),
        "review_status": "Needs director and producer review",
    }
    path = MASTER_DIR / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="MASTER")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = render_master(args.task_id)
    manifest_path = MASTER_DIR / "manifest.json"
    if args.quiet:
        print(str(manifest_path.relative_to(WORKSPACE)))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
