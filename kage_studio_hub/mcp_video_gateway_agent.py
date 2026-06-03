from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

try:
    from .provider_profile import provider_profile
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_profile import provider_profile


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
SUBMIT_GATE_PATH = PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json"
GATEWAY_DIR = PIPELINE_DIR / "mcp_video_gateway"
DISPATCH_QUEUE_PATH = GATEWAY_DIR / "mcp_video_dispatch_queue.jsonl"
MANIFEST_PATH = GATEWAY_DIR / "mcp_video_gateway_manifest.json"
REPORT_PATH = GATEWAY_DIR / "mcp_video_gateway_report.md"
SUBMIT_SCHEMA_PATH = GATEWAY_DIR / "schemas" / "submit_video_job.schema.json"
RESULT_SCHEMA_PATH = GATEWAY_DIR / "schemas" / "video_job_result.schema.json"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "allow", "enabled"}


def provider_env_prefix(provider: str) -> str:
    return f"KAGE_{provider.upper()}"


def bridge_command_env(provider: str) -> str:
    return f"{provider_env_prefix(provider)}_MCP_COMMAND"


def configured_bridge_command(provider: str) -> tuple[str, str]:
    provider_env = bridge_command_env(provider)
    provider_command = os.environ.get(provider_env, "").strip()
    if provider_command:
        return provider_env, provider_command
    global_env = "KAGE_MCP_VIDEO_GATEWAY_COMMAND"
    return global_env, os.environ.get(global_env, "").strip()


def mcp_payload(submission: dict) -> dict:
    provider = submission["provider"]
    profile = provider_profile(provider)
    return {
        "tool": "submit_video_job",
        "schema": rel(SUBMIT_SCHEMA_PATH),
        "result_schema": rel(RESULT_SCHEMA_PATH),
        "arguments": {
            "provider": provider,
            "profile_schema": profile.get("schema_version", ""),
            "model": os.environ.get(f"{provider_env_prefix(provider)}_MCP_MODEL", provider),
            "segment": submission.get("segment", ""),
            "shot_id": submission.get("shot_id", ""),
            "chunk_index": submission.get("chunk_index", 1),
            "duration_seconds": submission.get("duration_seconds", 0),
            "fps": 24,
            "resolution": "1920x1080",
            "keyframe_path": submission.get("source_keyframe", ""),
            "prompt": submission.get("motion_prompt", ""),
            "negative_prompt": submission.get("negative_prompt", ""),
            "expected_chunk_path": submission.get("expected_chunk_path", ""),
            "expected_final_inbox_path": submission.get("expected_final_inbox_path", ""),
            "safety_notes": [
                "Do not imitate protected franchise compositions or character designs.",
                "Return H.264 MP4 at 1920x1080, 24fps, matching the requested duration.",
                "Write or download the final accepted MP4 to expected_final_inbox_path.",
            ],
        },
    }


def run_bridge(command: str, payload: dict) -> dict:
    process = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=True,
        timeout=300,
        check=False,
    )
    parsed = {}
    if process.stdout.strip():
        try:
            parsed = json.loads(process.stdout)
        except json.JSONDecodeError:
            parsed = {"stdout": process.stdout.strip()}
    return {
        "returncode": process.returncode,
        "stdout_json": parsed,
        "stderr": process.stderr.strip(),
    }


def build_dispatch_item(provider_gate: dict, submission: dict, index: int, execute_enabled: bool) -> dict:
    provider = submission["provider"]
    command_env, command = configured_bridge_command(provider)
    provider_command_env = bridge_command_env(provider)
    global_command_env = "KAGE_MCP_VIDEO_GATEWAY_COMMAND"
    payload = mcp_payload(submission)
    dispatch_id = (
        f"{provider}_{submission.get('segment', 'segment')}_"
        f"{submission.get('shot_id', 'shot')}_chunk{submission.get('chunk_index', index):02d}"
    )
    base = {
        "dispatch_id": dispatch_id,
        "provider": provider,
        "segment": submission.get("segment", ""),
        "shot_id": submission.get("shot_id", ""),
        "chunk_index": submission.get("chunk_index", 1),
        "allowed_by_submit_gate": bool(provider_gate.get("allowed_to_submit")),
        "provider_bridge_command_env": provider_command_env,
        "global_bridge_command_env": global_command_env,
        "bridge_command_env_used": command_env,
        "bridge_configured": bool(command),
        "execute_enabled": execute_enabled,
        "mcp_tool": payload["tool"],
        "mcp_payload": payload,
        "expected_chunk_path": submission.get("expected_chunk_path", ""),
        "expected_final_inbox_path": submission.get("expected_final_inbox_path", ""),
    }
    if not provider_gate.get("allowed_to_submit"):
        return {**base, "status": "blocked_by_submit_gate", "blockers": provider_gate.get("blockers", [])}
    if not command:
        return {**base, "status": "prepared_mcp_dispatch_bridge_not_configured"}
    if not execute_enabled:
        return {**base, "status": "prepared_mcp_dispatch_execute_disabled"}
    result = run_bridge(command, payload)
    status = "submitted_via_mcp_bridge" if result["returncode"] == 0 else "mcp_bridge_failed"
    return {**base, "status": status, "bridge_result": result}


def build_report(manifest: dict) -> str:
    lines = [
        "# MCP Video Gateway Report",
        "",
        f"Task: {manifest['task_id']}",
        f"Mode: {manifest['mode']}",
        f"Dispatch items: {manifest['dispatch_count']}",
        f"Submitted via MCP bridge: {manifest['submitted_count']}",
        f"Prepared only: {manifest['prepared_count']}",
        f"Blocked: {manifest['blocked_count']}",
        "",
        "## Provider Summary",
        "",
        "| Provider | Dispatches | Submitted | Prepared | Blocked | Provider Bridge Env | Global Bridge Env |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in manifest["providers"]:
        lines.append(
            f"| {item['provider']} | {item['dispatch_count']} | {item['submitted_count']} | "
            f"{item['prepared_count']} | {item['blocked_count']} | "
            f"`{item['provider_bridge_command_env']}` | `{item['global_bridge_command_env']}` |"
        )
    lines.extend(
        [
            "",
            "## Execution Controls",
            "",
            "- No MCP bridge execution occurs unless `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC=true`.",
            "- Configure a global bridge command with `KAGE_MCP_VIDEO_GATEWAY_COMMAND`, or provider-specific commands like `KAGE_KLING_I2V_MCP_COMMAND`.",
            "- The bridge must accept one JSON payload on stdin and return JSON on stdout.",
            "- Returned MP4s must still land in the expected external-results inbox and pass ingest/review/replacement.",
        ]
    )
    return "\n".join(lines)


def run_gateway(task_id: str) -> dict:
    gate = load_json(SUBMIT_GATE_PATH, {})
    execute_enabled = env_bool("KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC")
    dispatch_items: list[dict] = []
    provider_summaries = []
    for provider_gate in gate.get("providers", []):
        queue_path = WORKSPACE / provider_gate.get("queue", "")
        submissions = load_jsonl(queue_path)
        provider_items = [
            build_dispatch_item(provider_gate, submission, index, execute_enabled)
            for index, submission in enumerate(submissions, start=1)
        ]
        dispatch_items.extend(provider_items)
        provider_summaries.append(
            {
                "provider": provider_gate.get("provider", ""),
                "dispatch_count": len(provider_items),
                "submitted_count": sum(1 for item in provider_items if item["status"] == "submitted_via_mcp_bridge"),
                "prepared_count": sum(1 for item in provider_items if item["status"].startswith("prepared_mcp_dispatch")),
                "blocked_count": sum(1 for item in provider_items if item["status"] == "blocked_by_submit_gate"),
                "provider_bridge_command_env": bridge_command_env(provider_gate.get("provider", "")),
                "global_bridge_command_env": "KAGE_MCP_VIDEO_GATEWAY_COMMAND",
            }
        )
    write_jsonl(DISPATCH_QUEUE_PATH, dispatch_items)
    manifest = {
        "task_id": task_id,
        "stage": "mcp_video_gateway",
        "mode": "execute_mcp_bridge" if execute_enabled else "prepare_only",
        "created_at": int(time.time()),
        "submit_gate": rel(SUBMIT_GATE_PATH) if SUBMIT_GATE_PATH.exists() else "",
        "dispatch_queue": rel(DISPATCH_QUEUE_PATH),
        "provider_count": len(provider_summaries),
        "dispatch_count": len(dispatch_items),
        "submitted_count": sum(1 for item in dispatch_items if item["status"] == "submitted_via_mcp_bridge"),
        "prepared_count": sum(1 for item in dispatch_items if item["status"].startswith("prepared_mcp_dispatch")),
        "blocked_count": sum(1 for item in dispatch_items if item["status"] == "blocked_by_submit_gate"),
        "failed_count": sum(1 for item in dispatch_items if item["status"] == "mcp_bridge_failed"),
        "providers": provider_summaries,
        "report": rel(REPORT_PATH),
        "next_step": (
            "Configure MCP bridge command plus submit gate approval/cost controls, then rerun gateway execution."
            if not execute_enabled
            else "Poll/download MCP provider results or place returned MP4s in the external-results inbox."
        ),
    }
    write_json(MANIFEST_PATH, manifest)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-MCP-VIDEO-GATEWAY")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_gateway(args.task_id)
    if args.quiet:
        print(rel(MANIFEST_PATH))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
