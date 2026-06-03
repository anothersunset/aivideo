from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .provider_env import token_env_candidates
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_env import token_env_candidates


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
LAUNCH_DIR = PIPELINE_DIR / "provider_launch" / "current_demo_hq_v01"
POLISH_QUEUE_PATH = PIPELINE_DIR / "polish_queue" / "polish_queue_manifest.json"
DIRECTOR_V02_PATH = PIPELINE_DIR / "director_review_v02" / "director_risk_review_v02_manifest.json"
CURRENT_DEMO_PATH = ANIME_PROJECT / "deliverables" / "current_demo" / "current_demo_manifest.json"
SUBMIT_GATE_PATH = PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json"
PROVIDER_REGISTRY_PATH = PIPELINE_DIR / "provider_registry.json"

PAID_PROVIDERS = {"kling_i2v", "seedance_i2v", "runway", "luma", "pika"}


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def env_provider_name(provider: str) -> str:
    return provider.upper()


def v02_keyframes() -> dict[tuple[str, str], dict]:
    review = load_json(DIRECTOR_V02_PATH, {})
    return {(item.get("segment", ""), item.get("shot_id", "")): item for item in review.get("keyframes", [])}


def choose_primary_route(queue_item: dict) -> dict:
    for route in queue_item.get("provider_routes", []):
        provider = route.get("provider", "")
        if provider in PAID_PROVIDERS and route.get("requires_submit_gate"):
            return route
    for route in queue_item.get("provider_routes", []):
        if route.get("provider") in PAID_PROVIDERS:
            return route
    raise ValueError(f"No paid provider route for {queue_item.get('queue_id')}")


def fallback_routes(queue_item: dict) -> list[dict]:
    return [
        route
        for route in queue_item.get("provider_routes", [])
        if route.get("provider") not in PAID_PROVIDERS or not route.get("requires_submit_gate")
    ]


def provider_gate(provider: str) -> dict:
    gate = load_json(SUBMIT_GATE_PATH, {})
    for item in gate.get("providers", []):
        if item.get("provider") == provider:
            return item
    return {}


def selected_launch_rows(task_id: str) -> list[dict]:
    queue = load_json(POLISH_QUEUE_PATH, {})
    keyframes = v02_keyframes()
    rows = []
    for item in queue.get("queue", []):
        route = choose_primary_route(item)
        provider = route["provider"]
        keyframe = keyframes.get((item["segment"], item["shot_id"]), {})
        gate = provider_gate(provider)
        env_name = env_provider_name(provider)
        rows.append(
            {
                "task_id": task_id,
                "queue_id": item["queue_id"],
                "priority": item.get("priority", ""),
                "segment": item["segment"],
                "shot_id": item["shot_id"],
                "label": item.get("label", ""),
                "provider": provider,
                "route": route.get("route", ""),
                "duration_seconds": item.get("duration_seconds", 0),
                "estimated_usd": route.get("estimated_usd", 0),
                "cost_cap_env": f"KAGE_{env_name}_COST_CAP_USD",
                "approval_env": f"KAGE_{env_name}_SUBMIT_APPROVED",
                "endpoint_env": f"KAGE_{env_name}_ENDPOINT",
                "token_env": f"KAGE_{env_name}_TOKEN",
                "token_env_candidates": token_env_candidates(provider),
                "source_frame": keyframe.get("frame") or item.get("source_frame", ""),
                "source_review_frame": keyframe.get("frame", ""),
                "motion_prompt": item.get("motion_prompt", ""),
                "safety_notes": item.get("safety_notes", []),
                "risk_rules": keyframe.get("risk_rules", []),
                "review_focus": keyframe.get("review_focus") or item.get("review_focus", ""),
                "fallback_routes": fallback_routes(item),
                "gate_status": {
                    "allowed_to_submit": gate.get("allowed_to_submit", False),
                    "blockers": gate.get("blockers", ["external_submit_gate_not_configured"]),
                    "checks": gate.get("checks", {}),
                },
                "expected_return_path": (
                    f"anime_project\\pipeline\\external_results\\inbox\\{provider}\\"
                    f"{item['segment']}\\{item['shot_id']}\\{item['shot_id']}_{provider}.mp4"
                ),
                "status": "launch_ready_blocked_by_submit_gate",
            }
        )
    return rows


def provider_config_template(rows: list[dict]) -> dict:
    by_provider = {}
    for row in rows:
        provider = row["provider"]
        entry = by_provider.setdefault(
            provider,
            {
                "enabled": False,
                "endpoint_env": row["endpoint_env"],
                "token_env": row["token_env"],
                "token_env_candidates": row["token_env_candidates"],
                "submit_approved_env": row["approval_env"],
                "cost_cap_env": row["cost_cap_env"],
                "suggested_cost_cap_usd": 0,
                "notes": "Fill endpoint/token/cost cap and set submit_approved only after producer approval.",
            },
        )
        entry["suggested_cost_cap_usd"] = round(entry["suggested_cost_cap_usd"] + float(row["estimated_usd"] or 0), 2)
    return {
        "stage": "external_provider_config_template",
        "policy": "No external submit is allowed until endpoint, token, approval, and cost cap are configured.",
        "providers": by_provider,
    }


def env_example(rows: list[dict]) -> str:
    lines = [
        "# Kage current demo high-quality provider launch env example",
        "# Copy values into your shell or private env file. Do not commit real secrets.",
        "",
        "KAGE_EXTERNAL_VIDEO_COST_CAP_USD=3.00",
        "",
    ]
    cost_by_provider: dict[str, float] = {}
    for row in rows:
        cost_by_provider[row["provider"]] = round(
            cost_by_provider.get(row["provider"], 0.0) + float(row.get("estimated_usd", 0) or 0),
            2,
        )
    seen = set()
    for row in rows:
        provider = row["provider"]
        if provider in seen:
            continue
        seen.add(provider)
        env_name = env_provider_name(provider)
        lines.extend(
            [
                f"# {provider}",
                f"KAGE_{env_name}_ENDPOINT=",
                f"KAGE_{env_name}_TOKEN=",
                f"# Backward-compatible alias also accepted: KAGE_{env_name}_API_KEY",
                f"KAGE_{env_name}_SUBMIT_APPROVED=false",
                f"KAGE_{env_name}_COST_CAP_USD={max(cost_by_provider[provider], 0.5):.2f}",
                "",
            ]
        )
    return "\n".join(lines)


def build_report(manifest: dict) -> str:
    lines = [
        "# High Quality Provider Launch Package",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Current demo: {manifest['current_demo']['current_version']}",
        f"Selected shots: {manifest['selected_shot_count']}",
        f"Selected providers: {manifest['selected_provider_count']}",
        f"Estimated first-pass paid cost: ${manifest['estimated_first_pass_cost_usd']}",
        "",
        "## Launch Rows",
        "",
        "| Queue | Shot | Provider | Cost | Gate | Return Path |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in manifest["launch_rows"]:
        gate = "ALLOW" if row["gate_status"]["allowed_to_submit"] else "BLOCKED"
        lines.append(
            f"| {row['queue_id']} | {row['segment']} / {row['shot_id']} | {row['provider']} | "
            f"${row['estimated_usd']} | {gate} | {row['expected_return_path']} |"
        )
    lines.extend(
        [
            "",
            "## Approval Controls",
            "",
            "- No external request has been submitted by this package.",
            "- Configure endpoint and token env vars for one provider first.",
            "- Preferred token env names use `KAGE_{PROVIDER}_TOKEN`; legacy `KAGE_{PROVIDER}_API_KEY` aliases are accepted.",
            "- Set provider approval env to true only after producer approval.",
            "- Set cost cap env at or above the selected provider estimate.",
            "- After returns arrive, run external ingest/review/replacement before updating the current demo.",
        ]
    )
    return "\n".join(lines)


def run_launch_package(task_id: str) -> dict:
    current_demo = load_json(CURRENT_DEMO_PATH, {})
    if current_demo.get("decision") != "producer_demo_v02_promoted_to_current_internal_demo":
        raise ValueError("current_demo is not promoted from reviewed v02")
    rows = selected_launch_rows(task_id)
    providers = sorted({row["provider"] for row in rows})
    estimated_cost = round(sum(float(row.get("estimated_usd", 0) or 0) for row in rows), 2)
    config_path = LAUNCH_DIR / "external_provider_config.current_demo_hq.template.json"
    env_path = LAUNCH_DIR / ".env.current_demo_hq.example"
    launch_rows_path = LAUNCH_DIR / "selected_provider_launch_rows.jsonl"
    write_json(config_path, provider_config_template(rows))
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(env_example(rows), encoding="utf-8")
    write_jsonl(launch_rows_path, rows)

    by_provider = {provider: [row for row in rows if row["provider"] == provider] for provider in providers}
    provider_packets = []
    for provider, provider_rows in by_provider.items():
        packet_path = LAUNCH_DIR / "providers" / f"{provider}_launch_packet.json"
        packet = {
            "provider": provider,
            "stage": "manual_or_api_launch_packet",
            "submission_policy": "Prepared only. Do not submit until gate checks pass.",
            "launch_rows": provider_rows,
        }
        write_json(packet_path, packet)
        provider_packets.append(
            {
                "provider": provider,
                "packet": rel(packet_path),
                "shot_count": len(provider_rows),
                "estimated_cost_usd": round(sum(float(row.get("estimated_usd", 0) or 0) for row in provider_rows), 2),
            }
        )

    manifest = {
        "task_id": task_id,
        "stage": "high_quality_provider_launch_package",
        "decision": "current_demo_hq_launch_ready_blocked_by_submit_gate",
        "current_demo": {
            "manifest": rel(CURRENT_DEMO_PATH),
            "current_version": current_demo.get("current_version", ""),
            "current_video": current_demo.get("current_video", ""),
            "current_zip": current_demo.get("current_zip", ""),
        },
        "source_polish_queue": rel(POLISH_QUEUE_PATH),
        "source_director_review_v02": rel(DIRECTOR_V02_PATH),
        "source_submit_gate": rel(SUBMIT_GATE_PATH),
        "source_provider_registry": rel(PROVIDER_REGISTRY_PATH),
        "selected_shot_count": len(rows),
        "selected_provider_count": len(providers),
        "estimated_first_pass_cost_usd": estimated_cost,
        "provider_packets": provider_packets,
        "launch_rows": rows,
        "config_template": rel(config_path),
        "env_example": rel(env_path),
        "selected_rows_jsonl": rel(launch_rows_path),
        "report": rel(LAUNCH_DIR / "high_quality_provider_launch_report.md"),
        "next_step": "Configure one provider endpoint/token/approval/cost cap, rerun ExternalSubmitGateAgent, then run ExternalProviderSubmitAgent.",
    }
    write_json(LAUNCH_DIR / "high_quality_provider_launch_manifest.json", manifest)
    (LAUNCH_DIR / "high_quality_provider_launch_report.md").write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-HQ-PROVIDER-LAUNCH")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_launch_package(args.task_id)
    if args.quiet:
        print(rel(LAUNCH_DIR / "high_quality_provider_launch_manifest.json"))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
