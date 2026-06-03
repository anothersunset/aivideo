from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .provider_profile import (
        extract_media_url,
        extract_provider_job_id as extract_profile_provider_job_id,
        extract_remote_status,
        provider_profile,
        success_statuses,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_profile import (
        extract_media_url,
        extract_provider_job_id as extract_profile_provider_job_id,
        extract_remote_status,
        provider_profile,
        success_statuses,
    )

try:
    from .provider_env import poll_endpoint_env, token_env, token_env_candidates, token_value
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_env import poll_endpoint_env, token_env, token_env_candidates, token_value


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
SUBMIT_RUN_PATH = PIPELINE_DIR / "submit_runs" / "external_video" / "submit_run_manifest.json"
POLL_RUN_DIR = PIPELINE_DIR / "poll_runs" / "external_video"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_provider_job_id(item: dict) -> str:
    response = item.get("provider_response", {}).get("response", {})
    provider = item.get("provider", "")
    return extract_profile_provider_job_id(provider, response) if isinstance(response, dict) else ""


def http_json_get(url: str, token: str, provider: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Kage-Provider": provider,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return {"status_code": response.status, "response": parsed}
    except urllib.error.URLError as exc:
        return {"status_code": 0, "error": str(exc)}


def poll_submitted_item(item: dict, http_enabled: bool) -> dict:
    provider = item["provider"]
    provider_job_id = extract_provider_job_id(item)
    base = {
        "submit_id": item.get("submit_id", ""),
        "provider": provider,
        "segment": item.get("segment", ""),
        "shot_id": item.get("shot_id", ""),
        "chunk_index": item.get("chunk_index", 1),
        "expected_chunk_path": item.get("expected_chunk_path", ""),
        "expected_final_inbox_path": item.get("expected_final_inbox_path", ""),
        "provider_job_id": provider_job_id,
    }
    if item.get("status") == "submit_prepared_http_disabled":
        return {**base, "status": "waiting_for_real_submit", "blocker": "http_submit_disabled"}
    if not provider_job_id:
        return {**base, "status": "waiting_for_provider_job_id", "blocker": "provider response has no job id"}
    if not http_enabled:
        return {**base, "status": "waiting_for_poll_enabled", "blocker": "poll http disabled"}
    poll_endpoint = os.environ.get(poll_endpoint_env(provider), "")
    token = token_value(provider)
    if not poll_endpoint or not token:
        return {
            **base,
            "status": "waiting_for_poll_config",
            "blocker": "missing poll endpoint or token",
            "poll_endpoint_env": poll_endpoint_env(provider),
            "token_env": token_env(provider),
            "token_env_candidates": token_env_candidates(provider),
        }
    separator = "&" if "?" in poll_endpoint else "?"
    url = f"{poll_endpoint}{separator}id={provider_job_id}"
    result = http_json_get(url, token, provider)
    response = result.get("response", {})
    media_url = extract_media_url(provider, response) if isinstance(response, dict) else ""
    remote_status = extract_remote_status(provider, response) if isinstance(response, dict) else ""
    if media_url and str(remote_status).lower() in success_statuses(provider):
        return {
            **base,
            "status": "ready_for_download",
            "poll_result": result,
            "media_url": media_url,
            "provider_profile": provider_profile(provider).get("schema_version", ""),
        }
    return {**base, "status": "poll_pending", "poll_result": result, "remote_status": remote_status}


def collect_submitted_items(submit_manifest: dict) -> list[dict]:
    submitted = []
    for provider_run in submit_manifest.get("provider_runs", []):
        submitted.extend(provider_run.get("submitted", []))
    return submitted


def run_poll(task_id: str) -> dict:
    submit_manifest = load_json(SUBMIT_RUN_PATH, {})
    submitted_items = collect_submitted_items(submit_manifest)
    poll_http_enabled = os.environ.get("KAGE_EXTERNAL_VIDEO_ENABLE_HTTP_POLL", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "allow",
    }
    poll_results = [poll_submitted_item(item, poll_http_enabled) for item in submitted_items]
    ready = [item for item in poll_results if item.get("status") == "ready_for_download"]
    pending = [item for item in poll_results if item.get("status") != "ready_for_download"]
    manifest = {
        "task_id": task_id,
        "stage": "external_provider_poll",
        "mode": "http_poll" if poll_http_enabled else "poll_disabled_status_only",
        "submit_manifest": rel(SUBMIT_RUN_PATH) if SUBMIT_RUN_PATH.exists() else "",
        "submitted_item_count": len(submitted_items),
        "ready_for_download_count": len(ready),
        "pending_count": len(pending),
        "downloaded_count": 0,
        "poll_results": poll_results,
        "next_step": (
            "No submitted provider jobs are available to poll. Run gate and submit after credentials/approval are configured."
            if not submitted_items
            else "Enable provider poll/download or place returned chunks in external_results/chunks, then run chunk assembly."
        ),
    }
    output = POLL_RUN_DIR / "poll_run_manifest.json"
    write_json(output, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-PROVIDER-POLL")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_poll(args.task_id)
    output = POLL_RUN_DIR / "poll_run_manifest.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
