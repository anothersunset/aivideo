#!/usr/bin/env python3
"""Generic HTTP MCP video bridge.

Reads one MCP-style submit_video_job payload from stdin and optionally submits
it to a provider HTTP endpoint. Safe by default: no external request is made
unless KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC=true.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .provider_env import endpoint_env, endpoint_value, token_env, token_env_candidates, token_value
    from .provider_profile import extract_media_url, extract_provider_job_id, extract_remote_status, success_statuses
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_env import endpoint_env, endpoint_value, token_env, token_env_candidates, token_value
    from provider_profile import extract_media_url, extract_provider_job_id, extract_remote_status, success_statuses


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
RESULT_SCHEMA = "anime_project\\pipeline\\mcp_video_gateway\\schemas\\video_job_result.schema.json"


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


def env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "allow", "enabled"}


def provider_request_body(payload: dict) -> dict:
    args = payload.get("arguments", {})
    return {
        "provider": args.get("provider", ""),
        "model": args.get("model", ""),
        "segment": args.get("segment", ""),
        "shot_id": args.get("shot_id", ""),
        "chunk_index": args.get("chunk_index", 1),
        "duration_seconds": args.get("duration_seconds", 0),
        "fps": args.get("fps", 24),
        "resolution": args.get("resolution", "1920x1080"),
        "keyframe_path": args.get("keyframe_path", ""),
        "prompt": args.get("prompt", ""),
        "negative_prompt": args.get("negative_prompt", ""),
        "expected_chunk_path": args.get("expected_chunk_path", ""),
        "expected_final_inbox_path": args.get("expected_final_inbox_path", ""),
        "safety_notes": args.get("safety_notes", []),
        "kage_payload_schema": payload.get("schema", ""),
    }


def http_submit(provider: str, payload: dict) -> dict:
    endpoint = endpoint_value(provider)
    token = token_value(provider)
    if not endpoint or not token:
        return {
            "status_code": 0,
            "error": "missing endpoint or token",
            "endpoint_env": endpoint_env(provider),
            "token_env": token_env(provider),
            "token_env_candidates": token_env_candidates(provider),
        }
    request_body = json.dumps(provider_request_body(payload), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Kage-Provider": provider,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            raw_body = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw_body)
            except json.JSONDecodeError:
                parsed = {"raw": raw_body}
            return {"status_code": response.status, "response": parsed}
    except urllib.error.URLError as exc:
        return {"status_code": 0, "error": str(exc)}


def bridge_result(payload: dict) -> dict:
    args = payload.get("arguments", {})
    provider = args.get("provider", "")
    base = {
        "schema": RESULT_SCHEMA,
        "provider": provider,
        "segment": args.get("segment", ""),
        "shot_id": args.get("shot_id", ""),
        "chunk_index": int(args.get("chunk_index", 1) or 1),
        "simulated": False,
        "external_api_call": False,
        "endpoint_env": endpoint_env(provider),
        "token_env": token_env(provider),
        "token_env_candidates": token_env_candidates(provider),
    }
    if not env_bool("KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC"):
        return {
            **base,
            "status": "queued",
            "job_id": f"mcp-http-bridge-disabled-{provider}-{int(time.time())}",
            "error": "KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC is not true; no external request was made",
        }
    result = http_submit(provider, payload)
    response = result.get("response", {})
    job_id = extract_provider_job_id(provider, response) if isinstance(response, dict) else ""
    remote_status = extract_remote_status(provider, response) if isinstance(response, dict) else ""
    media_url = extract_media_url(provider, response) if isinstance(response, dict) else ""
    ok = bool(result.get("status_code", 0)) and int(result["status_code"]) < 400
    completed = media_url and str(remote_status).lower() in success_statuses(provider)
    return {
        **base,
        "status": "completed" if completed else ("submitted" if ok else "failed"),
        "external_api_call": ok,
        "job_id": job_id or f"mcp-http-bridge-{provider}-{int(time.time())}",
        "video_url": media_url,
        "remote_status": remote_status,
        "provider_response_status_code": result.get("status_code", 0),
        "provider_response_summary": {
            "has_json_response": isinstance(response, dict),
            "keys": sorted(response.keys())[:20] if isinstance(response, dict) else [],
            "error": result.get("error", ""),
        },
        "expected_chunk_path": args.get("expected_chunk_path", ""),
        "expected_final_inbox_path": args.get("expected_final_inbox_path", ""),
    }


def main() -> None:
    payload = read_payload()
    print(json.dumps(bridge_result(payload), ensure_ascii=False))


if __name__ == "__main__":
    main()
