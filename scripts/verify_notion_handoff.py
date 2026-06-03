#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "NOTION_AI_HANDOFF.md",
    "AIVIDEO_PROJECT_OVERVIEW.md",
    "UPLOAD_MANIFEST.md",
    "anime_project/EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md",
    "anime_project/MCP_VIDEO_GATEWAY_PLAN.md",
    "kage_studio_hub/data/agent_tasks.json",
    "kage_studio_hub/mcp_video_gateway_agent.py",
    "kage_studio_hub/mcp_video_bridge_sim.py",
    "kage_studio_hub/mcp_http_video_bridge.py",
    "anime_project/pipeline/external_provider_profiles.json",
    "anime_project/pipeline/mcp_video_gateway/MCP_VIDEO_BRIDGE_CONTRACT.md",
    "anime_project/pipeline/mcp_video_gateway/schemas/submit_video_job.schema.json",
    "anime_project/pipeline/mcp_video_gateway/schemas/video_job_result.schema.json",
    "anime_project/pipeline/mcp_video_gateway/mcp_video_gateway_manifest.json",
    "anime_project/pipeline/mcp_video_gateway/rehearsals/kling_i2v_local_sim/mcp_video_gateway_rehearsal_report.md",
    "anime_project/pipeline/mcp_video_gateway/rehearsals/kling_i2v_local_sim/mcp_video_gateway_rehearsal_summary.json",
]

PLAYABLE_EVIDENCE_MP4S = [
    "anime_project/deliverables/current_demo/video/kage_current_demo.mp4",
    "anime_project/deliverables/producer_demo_v02/video/kage_preview_with_local_polish.mp4",
    "anime_project/deliverables/hq_provider_return_sim_v01/video/kage_preview_with_hq_sim_replacements.mp4",
    "anime_project/episode_segments/act2_01_sample/final/act2_01_sample_limited_animation.mp4",
    "anime_project/episode_segments/onsen_01_sample/final/onsen_01_sample_limited_animation.mp4",
    "anime_project/media/act2_storyboard_v02/act2_storyboard_v02_animatic.mp4",
]

MCP_REHEARSAL_MP4S = [
    "anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/act2_01_sample/08-004/08-004_kling_i2v_chunk01.mp4",
    "anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/onsen_01_sample/ON-008/ON-008_kling_i2v_chunk01.mp4",
    "anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/onsen_01_sample/ON-008/ON-008_kling_i2v_chunk02.mp4",
]


def normalize(raw: str) -> Path:
    return Path(PureWindowsPath(raw).as_posix())


def project_path(raw: str) -> Path:
    path = normalize(raw)
    return path if path.is_absolute() else ROOT / path


def assert_file(raw: str, *, min_bytes: int = 1) -> None:
    path = project_path(raw)
    if not path.exists():
        raise AssertionError(f"missing file: {raw}")
    if not path.is_file():
        raise AssertionError(f"not a file: {raw}")
    if path.stat().st_size < min_bytes:
        raise AssertionError(f"file too small: {raw} ({path.stat().st_size} bytes)")


def load_json(raw: str) -> dict:
    path = project_path(raw)
    return json.loads(path.read_text(encoding="utf-8"))


def ffprobe(raw: str) -> dict:
    if shutil.which("ffprobe") is None:
        raise AssertionError("ffprobe is required for media verification")
    path = project_path(raw)
    result = subprocess.run(
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
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    data = json.loads(result.stdout)
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    fmt = data.get("format", {})
    return {
        "codec_name": video.get("codec_name", ""),
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
        "r_frame_rate": video.get("r_frame_rate", ""),
        "duration_seconds": float(fmt.get("duration", 0) or 0),
        "size_bytes": int(fmt.get("size", 0) or 0),
    }


def verify_mp4(raw: str, *, strict_contract: bool) -> dict:
    assert_file(raw, min_bytes=100_000)
    probe = ffprobe(raw)
    if probe["codec_name"] != "h264":
        raise AssertionError(f"{raw}: expected h264, got {probe['codec_name']}")
    if strict_contract:
        if probe["width"] != 1920 or probe["height"] != 1080:
            raise AssertionError(f"{raw}: expected 1920x1080, got {probe['width']}x{probe['height']}")
        if probe["r_frame_rate"] != "24/1":
            raise AssertionError(f"{raw}: expected 24fps, got {probe['r_frame_rate']}")
    if probe["duration_seconds"] <= 0.5:
        raise AssertionError(f"{raw}: invalid duration {probe['duration_seconds']}")
    return probe


def backtick_paths(markdown: str) -> list[str]:
    paths = []
    for match in re.findall(r"`([^`]+)`", markdown):
        if "\n" in match or "\r" in match:
            continue
        if match.startswith(("http://", "https://", "KAGE_", "TASK-", "shot request")):
            continue
        if not match.startswith(("anime_project/", "anime_project\\", "kage_studio_hub/", "kage_studio_hub\\", "scripts/", "scripts\\", ".github/", ".github\\", "README.md", "NOTION_AI_HANDOFF.md", "AIVIDEO_PROJECT_OVERVIEW.md", "UPLOAD_MANIFEST.md")):
            continue
        if "\\" in match or "/" in match:
            if not any(ch in match for ch in "<>|*"):
                paths.append(match)
        elif match.endswith(".md"):
            paths.append(match)
    return paths


def verify_document_references() -> None:
    checked = set()
    for raw_doc in ["README.md", "NOTION_AI_HANDOFF.md"]:
        text = project_path(raw_doc).read_text(encoding="utf-8")
        for raw_path in backtick_paths(text):
            if raw_path.endswith("/") or raw_path.startswith("D:"):
                continue
            if raw_path in checked:
                continue
            checked.add(raw_path)
            assert_file(raw_path)


def verify_manifests() -> None:
    tasks = load_json("kage_studio_hub/data/agent_tasks.json")
    task_062 = next((task for task in tasks if task.get("id") == "TASK-062"), None)
    if not task_062:
        raise AssertionError("TASK-062 missing from agent_tasks.json")
    if task_062.get("agent") != "MCPVideoGatewayAgent":
        raise AssertionError("TASK-062 is not assigned to MCPVideoGatewayAgent")
    if task_062.get("review") != "Needs review":
        raise AssertionError("TASK-062 should remain Needs review until a real provider bridge is approved")

    gateway = load_json("anime_project/pipeline/mcp_video_gateway/mcp_video_gateway_manifest.json")
    if gateway.get("stage") != "mcp_video_gateway":
        raise AssertionError("MCP gateway manifest has wrong stage")
    if gateway.get("mode") != "prepare_only":
        raise AssertionError("main MCP gateway manifest must be restored to prepare_only")
    if gateway.get("dispatch_count") != 15 or gateway.get("blocked_count") != 15:
        raise AssertionError("main MCP gateway should show 15 blocked dispatches")
    dispatch_path = project_path("anime_project/pipeline/mcp_video_gateway/mcp_video_dispatch_queue.jsonl")
    dispatches = [json.loads(line) for line in dispatch_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(dispatches) != 15:
        raise AssertionError("MCP dispatch queue should contain 15 records")
    first_payload = dispatches[0].get("mcp_payload", {})
    if first_payload.get("schema") != "anime_project\\pipeline\\mcp_video_gateway\\schemas\\submit_video_job.schema.json":
        raise AssertionError("MCP payload does not reference submit_video_job schema")
    if first_payload.get("result_schema") != "anime_project\\pipeline\\mcp_video_gateway\\schemas\\video_job_result.schema.json":
        raise AssertionError("MCP payload does not reference video_job_result schema")

    rehearsal = load_json(
        "anime_project/pipeline/mcp_video_gateway/rehearsals/kling_i2v_local_sim/mcp_video_gateway_rehearsal_summary.json"
    )
    if rehearsal.get("decision") != "local_mcp_bridge_execution_proven_no_external_api_call":
        raise AssertionError("unexpected MCP rehearsal decision")
    if rehearsal.get("submitted_count") != 3 or rehearsal.get("failed_count") != 0:
        raise AssertionError("MCP rehearsal should submit 3 local chunks with 0 failures")
    if not rehearsal.get("main_gateway_restored_to_prepare_only") or not rehearsal.get("submit_gate_restored_to_blocked"):
        raise AssertionError("MCP rehearsal did not record restored safe state")
    for output in rehearsal.get("outputs", []):
        for key in ["provider", "segment", "shot_id", "chunk_index", "output_path", "probe"]:
            if key not in output:
                raise AssertionError(f"MCP rehearsal output missing {key}")
        sidecar = project_path(output["output_path"]).with_suffix(".mcp_bridge_sim.json")
        if not sidecar.exists():
            raise AssertionError(f"MCP bridge result sidecar missing: {sidecar}")
        sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
        if sidecar_payload.get("status") != "completed":
            raise AssertionError(f"MCP bridge result sidecar not completed: {sidecar}")
        if sidecar_payload.get("schema") and sidecar_payload.get("schema") != "anime_project\\pipeline\\mcp_video_gateway\\schemas\\video_job_result.schema.json":
            raise AssertionError(f"MCP bridge sidecar references unexpected schema: {sidecar}")

    submit_gate = load_json("anime_project/pipeline/submit_gate/external_submit_gate_manifest.json")
    if submit_gate.get("allowed_provider_count") != 0:
        raise AssertionError("submit gate should block all real providers by default")


def verify_http_bridge_safe_default() -> None:
    dispatch_path = project_path("anime_project/pipeline/mcp_video_gateway/mcp_video_dispatch_queue.jsonl")
    first_dispatch = next(
        json.loads(line)
        for line in dispatch_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    env = os.environ.copy()
    env.pop("KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC", None)
    result = subprocess.run(
        [sys.executable, "kage_studio_hub/mcp_http_video_bridge.py"],
        cwd=ROOT,
        input=json.dumps(first_dispatch),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    payload = json.loads(result.stdout)
    if payload.get("status") != "queued":
        raise AssertionError("HTTP MCP bridge should remain queued when execution is disabled")
    if payload.get("external_api_call"):
        raise AssertionError("HTTP MCP bridge made an external API call with execution disabled")
    if "KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC" not in payload.get("error", ""):
        raise AssertionError("HTTP MCP bridge did not explain its execution gate")
    combined = result.stdout + result.stderr
    if "TOKEN=" in combined or "API_KEY=" in combined:
        raise AssertionError("HTTP MCP bridge output appears to expose secret values")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-media", action="store_true", help="Skip ffprobe media verification.")
    args = parser.parse_args()

    for raw in REQUIRED_FILES:
        assert_file(raw)

    verify_document_references()
    verify_manifests()
    verify_http_bridge_safe_default()

    if not args.skip_media:
        for raw in PLAYABLE_EVIDENCE_MP4S:
            verify_mp4(raw, strict_contract=False)
        for raw in MCP_REHEARSAL_MP4S:
            verify_mp4(raw, strict_contract=True)

    print("Notion/GitHub handoff verification passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"handoff verification failed: {exc}", file=sys.stderr)
        raise
