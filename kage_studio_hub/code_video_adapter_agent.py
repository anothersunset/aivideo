from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
PROVIDER_RUNS_DIR = PIPELINE_DIR / "provider_runs"
EXTERNAL_INBOX = PIPELINE_DIR / "external_results" / "inbox"
ADAPTER_RUNS_DIR = PIPELINE_DIR / "adapter_runs"

DEFAULT_TARGETS = [
    ("onsen_01_sample", "ON-008"),
    ("act2_01_sample", "08-004"),
]


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_resolution(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def target_set(selected_only: bool, segment: str | None, shot_id: str | None) -> set[tuple[str, str]] | None:
    if segment and shot_id:
        return {(segment, shot_id)}
    if selected_only:
        return set(DEFAULT_TARGETS)
    return None


def iter_remotion_packets(targets: set[tuple[str, str]] | None) -> list[Path]:
    packets = sorted(PROVIDER_RUNS_DIR.glob("remotion/*/*_remotion_props.json"))
    if targets is None:
        return packets
    selected = []
    for path in packets:
        packet = load_json(path)
        segment = path.parent.name
        shot_id = packet.get("props", {}).get("shotId", "")
        if (segment, shot_id) in targets:
            selected.append(path)
    return selected


def render_code_video(packet_path: Path, task_id: str) -> dict:
    packet = load_json(packet_path)
    props = packet["props"]
    segment = packet_path.parent.name
    shot_id = props["shotId"]
    duration = float(props.get("durationSeconds", packet.get("duration_seconds", 2.0)))
    fps = int(packet.get("fps", 24))
    width, height = parse_resolution(packet.get("resolution", "1920x1080"))
    source = WORKSPACE / props["sourceVideo"]
    output = EXTERNAL_INBOX / "remotion" / segment / shot_id / f"{shot_id}_remotion.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    # This is a real local code-video adapter pass: it consumes Remotion-style props,
    # keeps the approved fallback motion, and applies repeatable production packaging.
    filter_graph = (
        f"fps={fps},"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        "eq=contrast=1.13:saturation=0.86:brightness=-0.025,"
        "unsharp=5:5:0.55,"
        "vignette=PI/5,"
        "format=yuv420p"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            filter_graph,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
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
    return {
        "task_id": task_id,
        "provider": "remotion",
        "adapter": "code_video_adapter_agent.py",
        "segment": segment,
        "shot_id": shot_id,
        "source_packet": rel(packet_path),
        "source_video": props["sourceVideo"],
        "output": rel(output),
        "duration_seconds": duration,
        "fps": fps,
        "resolution": f"{width}x{height}",
        "status": "rendered_to_external_inbox",
    }


def run_adapter(task_id: str, selected_only: bool, segment: str | None, shot_id: str | None) -> dict:
    targets = target_set(selected_only, segment, shot_id)
    packet_paths = iter_remotion_packets(targets)
    rendered = [render_code_video(path, task_id) for path in packet_paths]
    manifest = {
        "task_id": task_id,
        "stage": "code_video_provider_adapter",
        "mode": "real_local_code_render_no_external_api_call",
        "provider": "remotion",
        "selected_only": selected_only,
        "rendered_count": len(rendered),
        "external_inbox": rel(EXTERNAL_INBOX / "remotion"),
        "renders": rendered,
        "next_step": "Run ExternalResultIngestAgent scan; accepted renders can become approved replacements.",
    }
    output_path = ADAPTER_RUNS_DIR / "code_video_adapter_manifest.json"
    write_json(output_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-CODEVIDEO")
    parser.add_argument("--selected-only", action="store_true")
    parser.add_argument("--segment")
    parser.add_argument("--shot-id")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_adapter(args.task_id, args.selected_only, args.segment, args.shot_id)
    output_path = ADAPTER_RUNS_DIR / "code_video_adapter_manifest.json"
    if args.quiet:
        print(rel(output_path))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
