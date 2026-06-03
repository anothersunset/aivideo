from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

try:
    from .provider_env import configured_env_name, endpoint_env, endpoint_value, token_env_candidates, token_value
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_env import configured_env_name, endpoint_env, endpoint_value, token_env_candidates, token_value


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
ADAPTER_RUNS_DIR = PIPELINE_DIR / "adapter_runs"
EXTERNAL_VIDEO_DIR = ADAPTER_RUNS_DIR / "external_video"
GATE_DIR = PIPELINE_DIR / "submit_gate"

DEFAULT_RATES_PER_SECOND = {
    "kling_i2v": 0.18,
    "seedance_i2v": 0.18,
    "runway": 0.24,
    "luma": 0.22,
    "pika": 0.16,
}


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "approved", "allow"}


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def provider_rate(provider: str) -> float:
    env_name = f"KAGE_{provider.upper()}_EST_USD_PER_SECOND"
    return env_float(env_name, DEFAULT_RATES_PER_SECOND.get(provider, 0.25))


def provider_queue_manifest(provider_dir: Path) -> dict:
    manifest = load_json(provider_dir / "run_manifest.json", {})
    queue_path = WORKSPACE / manifest.get("queue", "")
    submissions = load_jsonl(queue_path)
    seconds = sum(float(item.get("duration_seconds", 0) or 0) for item in submissions)
    rate = provider_rate(provider_dir.name)
    estimated_cost = round(seconds * rate, 2)
    readiness = manifest.get("readiness", {})
    approval_env = f"KAGE_{provider_dir.name.upper()}_SUBMIT_APPROVED"
    endpoint_name = endpoint_env(provider_dir.name)
    token_candidates = token_env_candidates(provider_dir.name)
    token_name_used = configured_env_name(token_candidates)
    has_endpoint = bool(endpoint_value(provider_dir.name))
    has_token = bool(token_value(provider_dir.name))
    submit_approved = env_bool(approval_env)
    cost_cap = env_float(f"KAGE_{provider_dir.name.upper()}_COST_CAP_USD", env_float("KAGE_EXTERNAL_VIDEO_COST_CAP_USD", 0.0))
    checks = {
        "has_endpoint": has_endpoint,
        "has_token": has_token,
        "submit_approved": submit_approved,
        "cost_cap_configured": cost_cap > 0,
        "cost_within_cap": cost_cap > 0 and estimated_cost <= cost_cap,
        "has_submissions": bool(submissions),
    }
    allowed = all(checks.values())
    blockers = [key for key, value in checks.items() if not value]
    return {
        "provider": provider_dir.name,
        "queue": manifest.get("queue", ""),
        "manual_submission_packet": manifest.get("manual_submission_packet", ""),
        "submission_count": len(submissions),
        "total_duration_seconds": round(seconds, 3),
        "estimated_usd_per_second": rate,
        "estimated_cost_usd": estimated_cost,
        "cost_cap_usd": cost_cap,
        "approval_env": approval_env,
        "endpoint_env": endpoint_name,
        "token_env": token_name_used or token_candidates[0],
        "token_env_candidates": token_candidates,
        "token_env_used": token_name_used,
        "adapter_readiness": readiness,
        "checks": checks,
        "allowed_to_submit": allowed,
        "blockers": blockers,
    }


def write_approval_request(providers: list[dict], task_id: str) -> str:
    lines = [
        "# External Video Submit Approval Request",
        "",
        f"Task: {task_id}",
        "",
        "No external request is submitted by this gate. A provider is allowed only when endpoint, token, approval, and cost cap are all present.",
        "",
        "| Provider | Chunks | Seconds | Est. Cost | Cap | Status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in providers:
        status = "ALLOW" if item["allowed_to_submit"] else "BLOCKED: " + ", ".join(item["blockers"])
        lines.append(
            f"| {item['provider']} | {item['submission_count']} | {item['total_duration_seconds']} | "
            f"${item['estimated_cost_usd']} | ${item['cost_cap_usd']} | {status} |"
        )
    lines.extend(
        [
            "",
            "Approval controls:",
            "",
            "- Set `KAGE_{PROVIDER}_SUBMIT_APPROVED=true` only after producer/director approval.",
            "- Set `KAGE_{PROVIDER}_COST_CAP_USD` or `KAGE_EXTERNAL_VIDEO_COST_CAP_USD` before submit.",
            "- Set `KAGE_{PROVIDER}_TOKEN`; older `KAGE_{PROVIDER}_API_KEY` names are still accepted.",
            "- Keep returned chunks under `anime_project/pipeline/external_results/chunks/...`.",
            "- Run `ExternalChunkAssemblyAgent`, then `ExternalResultIngestAgent`, then replacement review.",
        ]
    )
    path = GATE_DIR / "external_submit_approval_request.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return rel(path)


def evaluate_gate(task_id: str) -> dict:
    provider_dirs = sorted(path for path in EXTERNAL_VIDEO_DIR.iterdir() if path.is_dir())
    providers = [provider_queue_manifest(path) for path in provider_dirs]
    allowed = [item for item in providers if item["allowed_to_submit"]]
    blocked = [item for item in providers if not item["allowed_to_submit"]]
    manifest = {
        "task_id": task_id,
        "stage": "external_submit_gate",
        "mode": "approval_and_cost_gate",
        "created_at": int(time.time()),
        "provider_count": len(providers),
        "allowed_provider_count": len(allowed),
        "blocked_provider_count": len(blocked),
        "total_submission_count": sum(item["submission_count"] for item in providers),
        "total_estimated_cost_usd": round(sum(item["estimated_cost_usd"] for item in providers), 2),
        "providers": providers,
        "approval_request": "",
        "next_step": "Configure one provider endpoint/token, approval flag, and cost cap before any external submit.",
    }
    manifest["approval_request"] = write_approval_request(providers, task_id)
    output = GATE_DIR / "external_submit_gate_manifest.json"
    write_json(output, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-SUBMIT-GATE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = evaluate_gate(args.task_id)
    output = GATE_DIR / "external_submit_gate_manifest.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
