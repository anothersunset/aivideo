from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
SUBMIT_GATE_PATH = PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json"
SUBMIT_RUN_DIR = PIPELINE_DIR / "submit_runs" / "external_video"


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


def endpoint_env(provider: str) -> str:
    if provider == "seedance_i2v":
        return "KAGE_SEEDANCE_I2V_ENDPOINT"
    return f"KAGE_{provider.upper()}_ENDPOINT"


def token_env(provider: str) -> str:
    if provider == "seedance_i2v":
        return "KAGE_SEEDANCE_I2V_API_KEY"
    return f"KAGE_{provider.upper()}_API_KEY"


def http_submit(provider: str, submission: dict) -> dict:
    endpoint = os.environ[endpoint_env(provider)]
    token = os.environ[token_env(provider)]
    payload = json.dumps(submission, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Kage-Provider": provider,
        },
        method="POST",
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


def submit_allowed_provider(provider_gate: dict, task_id: str, http_enabled: bool) -> dict:
    provider = provider_gate["provider"]
    queue_path = WORKSPACE / provider_gate["queue"]
    submissions = load_jsonl(queue_path)
    submitted = []
    failed = []
    for index, submission in enumerate(submissions, start=1):
        submit_id = f"{task_id}_{provider}_{index:03d}_{submission['shot_id']}_chunk{submission['chunk_index']:02d}"
        base = {
            "submit_id": submit_id,
            "provider": provider,
            "segment": submission["segment"],
            "shot_id": submission["shot_id"],
            "chunk_index": submission["chunk_index"],
            "duration_seconds": submission["duration_seconds"],
            "expected_chunk_path": submission["expected_chunk_path"],
            "expected_final_inbox_path": submission["expected_final_inbox_path"],
        }
        if http_enabled:
            result = http_submit(provider, {**submission, "submit_id": submit_id})
            if result.get("status_code", 0) and int(result["status_code"]) < 400:
                submitted.append({**base, "status": "submitted_http", "provider_response": result})
            else:
                failed.append({**base, "status": "submit_failed", "provider_response": result})
        else:
            submitted.append({**base, "status": "submit_prepared_http_disabled"})
    return {
        "provider": provider,
        "allowed_to_submit": True,
        "queue": provider_gate["queue"],
        "submission_count": len(submissions),
        "submitted_count": len(submitted),
        "failed_count": len(failed),
        "submitted": submitted,
        "failed": failed,
    }


def run_submit(task_id: str) -> dict:
    gate = load_json(SUBMIT_GATE_PATH, {})
    providers = gate.get("providers", [])
    allowed = [provider for provider in providers if provider.get("allowed_to_submit")]
    blocked = [provider for provider in providers if not provider.get("allowed_to_submit")]
    http_enabled = os.environ.get("KAGE_EXTERNAL_VIDEO_ENABLE_HTTP_SUBMIT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "allow",
    }
    provider_runs = [submit_allowed_provider(provider, task_id, http_enabled) for provider in allowed]
    manifest = {
        "task_id": task_id,
        "stage": "external_provider_submit",
        "mode": "http_submit" if http_enabled else "prepare_only_http_disabled",
        "created_at": int(time.time()),
        "gate_manifest": rel(SUBMIT_GATE_PATH) if SUBMIT_GATE_PATH.exists() else "",
        "allowed_provider_count": len(allowed),
        "blocked_provider_count": len(blocked),
        "submitted_count": sum(item["submitted_count"] for item in provider_runs),
        "failed_count": sum(item["failed_count"] for item in provider_runs),
        "blocked_providers": [
            {
                "provider": item["provider"],
                "blockers": item.get("blockers", []),
                "queue": item.get("queue", ""),
                "manual_submission_packet": item.get("manual_submission_packet", ""),
            }
            for item in blocked
        ],
        "provider_runs": provider_runs,
        "next_step": (
            "Poll/download submitted provider jobs, then place returned chunks in external_results/chunks."
            if provider_runs
            else "No provider passed the submit gate. Configure credentials, approval, and cost cap, then re-run the gate."
        ),
    }
    output = SUBMIT_RUN_DIR / "submit_run_manifest.json"
    write_json(output, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-PROVIDER-SUBMIT")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_submit(args.task_id)
    output = SUBMIT_RUN_DIR / "submit_run_manifest.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
