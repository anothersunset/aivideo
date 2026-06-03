#!/usr/bin/env python3
"""Local MCP video bridge simulation.

Reads one MCP-style submit_video_job payload from stdin and writes a real H.264
MP4 chunk. This is a local execution rehearsal only: no external API call, no
HTTP request, no token use.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

try:
    from .pipeline_common import FPS, HEIGHT, WIDTH, resolve_workspace_path, run_checked
except ImportError:  # pragma: no cover - supports direct script execution.
    from pipeline_common import FPS, HEIGHT, WIDTH, resolve_workspace_path, run_checked


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME = WORKSPACE / "anime_project"
PIPE = ANIME / "pipeline"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("stdin is empty; expected MCP submit_video_job JSON")
    payload = json.loads(raw)
    if "mcp_payload" in payload:
        payload = payload["mcp_payload"]
    if payload.get("tool") != "submit_video_job":
        raise ValueError(f"unsupported tool: {payload.get('tool')}")
    return payload


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("no source keyframe fallback exists")


def source_keyframe(args: dict) -> Path:
    segment = args.get("segment", "")
    shot_id = args.get("shot_id", "")
    raw = args.get("keyframe_path", "")
    candidates = []
    if raw:
        candidates.append(resolve_workspace_path(WORKSPACE, raw))
    candidates.extend(
        [
            PIPE / "director_review_v02" / "keyframes" / segment / f"{shot_id}_v02_master_mid.png",
            PIPE / "director_review" / "keyframes" / segment / f"{shot_id}_master_mid.png",
        ]
    )
    package_keyframes = ANIME / "deliverables" / "provider_launch" / "current_demo_hq_v01" / "keyframes"
    candidates.extend(sorted(package_keyframes.glob(f"*_{segment}_{shot_id}.png")))
    candidates.extend(
        [
            ANIME / "episode_segments" / segment / "layers" / f"{shot_id}_char.png",
            ANIME / "episode_segments" / segment / "layers" / f"{shot_id}_bg.png",
        ]
    )
    return first_existing(candidates)


def output_path(args: dict) -> Path:
    raw = args.get("expected_chunk_path") or args.get("expected_final_inbox_path")
    if not raw:
        raise ValueError("payload missing expected_chunk_path / expected_final_inbox_path")
    output = resolve_workspace_path(WORKSPACE, raw)
    override_root = os.environ.get("KAGE_MCP_BRIDGE_SIM_OUTPUT_ROOT", "").strip()
    if override_root:
        root = resolve_workspace_path(WORKSPACE, override_root)
        relative = output.relative_to(WORKSPACE)
        output = root / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def ffprobe(path: Path) -> dict:
    result = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,r_frame_rate",
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
        "duration_seconds": round(float(fmt.get("duration", 0) or 0), 3),
        "size_bytes": int(fmt.get("size", 0) or 0),
    }


def render_from_keyframe(source: Path, output: Path, duration: float, provider: str) -> None:
    grade = {
        "kling_i2v": "eq=contrast=1.11:saturation=0.90:brightness=-0.012,unsharp=5:5:0.45",
        "pika": "eq=contrast=1.06:saturation=1.02:brightness=0.004,unsharp=3:3:0.35",
        "runway": "eq=contrast=1.09:saturation=0.95:brightness=-0.008,unsharp=3:3:0.40",
        "luma": "eq=contrast=1.08:saturation=0.98:brightness=-0.004,unsharp=3:3:0.35",
        "seedance_i2v": "eq=contrast=1.12:saturation=0.90:brightness=-0.014,unsharp=5:5:0.45",
    }.get(provider, "eq=contrast=1.06:saturation=0.95,unsharp=3:3:0.35")
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        "zoompan=z='1+0.018*sin(on/18)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:fps={FPS}:s={WIDTH}x{HEIGHT},"
        f"{grade},format=yuv420p"
    )
    run_checked(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
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


def main() -> None:
    payload = read_payload()
    args = payload.get("arguments", {})
    provider = args.get("provider", "mcp_local_sim")
    duration = float(args.get("duration_seconds", 2.0) or 2.0)
    source = source_keyframe(args)
    output = output_path(args)
    render_from_keyframe(source, output, duration, provider)
    if os.environ.get("KAGE_MCP_BRIDGE_SIM_WRITE_FINAL", "").strip().lower() in {"1", "true", "yes"}:
        final_raw = args.get("expected_final_inbox_path", "")
        if final_raw:
            final_output = resolve_workspace_path(WORKSPACE, final_raw)
            final_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(output, final_output)
    probe = ffprobe(output)
    result = {
        "status": "completed",
        "simulated": True,
        "external_api_call": False,
        "job_id": f"mcp-local-sim-{provider}-{args.get('segment', '')}-{args.get('shot_id', '')}-{int(time.time())}",
        "provider": provider,
        "segment": args.get("segment", ""),
        "shot_id": args.get("shot_id", ""),
        "chunk_index": args.get("chunk_index", 1),
        "source_keyframe": rel(source),
        "output_path": rel(output),
        "video_url": f"file:///{output.as_posix()}",
        "probe": probe,
    }
    sidecar = output.with_suffix(".mcp_bridge_sim.json")
    sidecar.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
