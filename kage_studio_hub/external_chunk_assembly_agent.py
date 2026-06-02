from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
ADAPTER_RUNS_DIR = PIPELINE_DIR / "adapter_runs"
EXTERNAL_VIDEO_DIR = ADAPTER_RUNS_DIR / "external_video"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def group_submissions() -> dict[tuple[str, str, str], list[dict]]:
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for packet_path in sorted(EXTERNAL_VIDEO_DIR.glob("*/manual_submission_packet.json")):
        packet = load_json(packet_path)
        for item in packet.get("submissions", []):
            key = (item["provider"], item["segment"], item["shot_id"])
            groups.setdefault(key, []).append(item)
    for items in groups.values():
        items.sort(key=lambda item: int(item.get("chunk_index", 1)))
    return groups


def concat_chunks(chunks: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if len(chunks) == 1:
        shutil.copyfile(chunks[0], output)
        return
    concat_path = output.parent / f"{output.stem}_chunks.txt"
    concat_path.write_text("\n".join(f"file '{path.resolve().as_posix()}'" for path in chunks), encoding="utf-8")
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
            str(output),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def assemble(task_id: str) -> dict:
    assembled = []
    waiting = []
    for (provider, segment, shot_id), submissions in group_submissions().items():
        chunk_paths = [WORKSPACE / item["expected_chunk_path"] for item in submissions]
        missing = [rel(path) for path in chunk_paths if not path.exists()]
        final_path = WORKSPACE / submissions[0]["expected_final_inbox_path"]
        record = {
            "provider": provider,
            "segment": segment,
            "shot_id": shot_id,
            "chunk_count": len(submissions),
            "final_inbox_path": rel(final_path),
        }
        if missing:
            waiting.append({**record, "missing_chunks": missing, "status": "waiting_for_chunks"})
            continue
        concat_chunks(chunk_paths, final_path)
        assembled.append({**record, "status": "assembled_to_inbox"})
    manifest = {
        "task_id": task_id,
        "stage": "external_chunk_assembly",
        "assembled_count": len(assembled),
        "waiting_count": len(waiting),
        "assembled": assembled,
        "waiting": waiting,
        "next_step": "Run ExternalResultIngestAgent after any assembled files appear in the external inbox.",
    }
    output = EXTERNAL_VIDEO_DIR / "chunk_assembly_manifest.json"
    write_json(output, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-CHUNK-ASSEMBLY")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = assemble(args.task_id)
    output = EXTERNAL_VIDEO_DIR / "chunk_assembly_manifest.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
