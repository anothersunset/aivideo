from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
POLISH_DIR = PIPELINE_DIR / "polish_queue"
HANDOFF_DIR = POLISH_DIR / "handoff_cards"
PACKET_PATH = POLISH_DIR / "provider_handoff_packets.jsonl"
MANIFEST_PATH = POLISH_DIR / "polish_queue_manifest.json"
REPORT_PATH = POLISH_DIR / "polish_work_order.md"

DIRECTOR_REVIEW_PATH = PIPELINE_DIR / "director_review" / "director_risk_review_manifest.json"
PRODUCER_PACKAGE_PATH = ANIME_PROJECT / "deliverables" / "producer_demo_v01" / "producer_demo_manifest.json"
PROVIDER_REGISTRY_PATH = PIPELINE_DIR / "provider_registry.json"
SUBMIT_GATE_PATH = PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json"


PROVIDER_PROFILES = {
    "kling_i2v": {"estimated_usd_per_second": 0.18, "route": "primary_i2v_motion"},
    "seedance_i2v": {"estimated_usd_per_second": 0.18, "route": "alternate_i2v_motion"},
    "runway": {"estimated_usd_per_second": 0.24, "route": "premium_motion_variant"},
    "luma": {"estimated_usd_per_second": 0.22, "route": "cinematic_camera_variant"},
    "pika": {"estimated_usd_per_second": 0.16, "route": "fast_short_variant"},
    "remotion": {"estimated_usd_per_second": 0.0, "route": "local_code_video_baseline"},
    "comfyui_svd": {"estimated_usd_per_second": 0.0, "route": "local_open_source_test"},
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


def shot_priority(item: dict) -> str:
    if item.get("replacement_provider"):
        return "P0"
    if item.get("shot_id") in {"08-003", "11-004", "12-002"}:
        return "P1"
    return "P2"


def recommended_providers(item: dict) -> list[str]:
    shot_id = item.get("shot_id", "")
    if item.get("replacement_provider"):
        return ["kling_i2v", "seedance_i2v", "runway", "remotion"]
    if shot_id == "08-003":
        return ["remotion", "comfyui_svd", "kling_i2v"]
    if shot_id == "11-004":
        return ["kling_i2v", "seedance_i2v", "comfyui_svd"]
    if shot_id == "12-002":
        return ["remotion", "comfyui_svd", "pika"]
    return ["remotion"]


def motion_prompt(item: dict) -> str:
    shot_id = item.get("shot_id", "")
    base = {
        "ON-008": "Rainy onsen action beat, sharp 2D limited-animation silhouette motion, blade impact readable through rain, no camera chaos, preserve dark restrained palette.",
        "08-003": "Hidden impact beat, no face and no pain expression, communicate danger through props, silhouette timing, and one clean action accent.",
        "08-004": "Iron centipede creature motion test, low dark silhouette, segmented body readability, one strong strike rhythm, restrained horror.",
        "11-004": "Hirumaru parasite staging, keep parasite count at or below eight, clear body spacing, readable threat without gore escalation.",
        "12-002": "Chiyo restraint beat, silent emotional acting through hands and props, no child pain process, still rain atmosphere.",
    }.get(shot_id, item.get("review_focus", "Polish motion and readability while preserving project style."))
    return (
        f"{base} Match the existing master timing, 1920x1080, 24fps, 2D limited anime look, "
        "original character design only, no imitation of known franchise compositions."
    )


def safety_notes(item: dict) -> list[str]:
    notes = [
        "Preserve original project identity; do not copy protected character designs or iconic compositions.",
        "Return H.264 MP4 at 1920x1080 and 24fps, matching shot duration.",
        "Do not submit to paid providers until submit gate approval and cost cap are configured.",
    ]
    notes.extend(item.get("risk_rules", []))
    if item.get("replacement_provider"):
        notes.append("Current replacement is workflow-approved only; high-quality vendor output still requires director review.")
    return notes


def build_queue_item(item: dict, index: int) -> dict:
    providers = recommended_providers(item)
    duration = float(item.get("duration_seconds", 0) or 0)
    external_cost = sum(
        PROVIDER_PROFILES.get(provider, {}).get("estimated_usd_per_second", 0.0) * duration
        for provider in providers
    )
    return {
        "queue_id": f"POLISH-{index:03d}",
        "priority": shot_priority(item),
        "segment": item.get("segment", ""),
        "shot_id": item.get("shot_id", ""),
        "label": item.get("label", ""),
        "duration_seconds": duration,
        "source_frame": item.get("frame", ""),
        "review_focus": item.get("review_focus", ""),
        "motion_prompt": motion_prompt(item),
        "safety_notes": safety_notes(item),
        "recommended_providers": providers,
        "provider_routes": [
            {
                "provider": provider,
                "route": PROVIDER_PROFILES.get(provider, {}).get("route", "custom"),
                "estimated_usd": round(PROVIDER_PROFILES.get(provider, {}).get("estimated_usd_per_second", 0.0) * duration, 3),
                "requires_submit_gate": PROVIDER_PROFILES.get(provider, {}).get("estimated_usd_per_second", 0.0) > 0,
            }
            for provider in providers
        ],
        "estimated_external_cost_usd": round(external_cost, 3),
        "status": "ready_for_handoff_not_submitted",
    }


def write_handoff_card(item: dict) -> str:
    path = HANDOFF_DIR / f"{item['queue_id']}_{item['segment']}_{item['shot_id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {item['queue_id']} {item['segment']} / {item['shot_id']}",
        "",
        f"Priority: {item['priority']}",
        f"Duration: {item['duration_seconds']}s",
        f"Source frame: {item['source_frame']}",
        "",
        "## Motion Prompt",
        "",
        item["motion_prompt"],
        "",
        "## Providers",
        "",
    ]
    for route in item["provider_routes"]:
        gate = "submit gate required" if route["requires_submit_gate"] else "local/no paid gate"
        lines.append(f"- {route['provider']}: {route['route']}, ${route['estimated_usd']} estimate, {gate}")
    lines.extend(["", "## Safety Notes", ""])
    for note in item["safety_notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return rel(path)


def write_packets(queue: list[dict]) -> None:
    PACKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PACKET_PATH.open("w", encoding="utf-8") as handle:
        for item in queue:
            for route in item["provider_routes"]:
                packet = {
                    "queue_id": item["queue_id"],
                    "segment": item["segment"],
                    "shot_id": item["shot_id"],
                    "provider": route["provider"],
                    "source_frame": item["source_frame"],
                    "duration_seconds": item["duration_seconds"],
                    "motion_prompt": item["motion_prompt"],
                    "safety_notes": item["safety_notes"],
                    "estimated_usd": route["estimated_usd"],
                    "requires_submit_gate": route["requires_submit_gate"],
                    "status": "prepared_not_submitted",
                }
                handle.write(json.dumps(packet, ensure_ascii=False) + "\n")


def build_report(manifest: dict) -> str:
    lines = [
        "# High Quality Polish Work Order",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Queue items: {manifest['queue_count']}",
        f"Provider packets: {manifest['provider_packet_count']}",
        f"Estimated external cost: ${manifest['estimated_external_cost_usd']}",
        "",
        "## Gate Status",
        "",
        f"- Submit gate allowed providers: {manifest['submit_gate']['allowed_provider_count']}",
        f"- Submit gate blocked providers: {manifest['submit_gate']['blocked_provider_count']}",
        "- This work order prepares handoff packets only; it does not spend external provider credits.",
        "",
        "## Queue",
        "",
        "| Queue | Priority | Shot | Providers | Cost | Card |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for item in manifest["queue"]:
        lines.append(
            f"| {item['queue_id']} | {item['priority']} | {item['segment']} / {item['shot_id']} | "
            f"{', '.join(item['recommended_providers'])} | ${item['estimated_external_cost_usd']} | {item['handoff_card']} |"
        )
    return "\n".join(lines)


def run_queue(task_id: str) -> dict:
    director_review = load_json(DIRECTOR_REVIEW_PATH, {})
    producer_package = load_json(PRODUCER_PACKAGE_PATH, {})
    provider_registry = load_json(PROVIDER_REGISTRY_PATH, {})
    submit_gate = load_json(SUBMIT_GATE_PATH, {})
    keyframes = [item for item in director_review.get("keyframes", []) if item.get("metrics", {}).get("nonblank")]
    queue = [build_queue_item(item, index + 1) for index, item in enumerate(keyframes)]
    for item in queue:
        item["handoff_card"] = write_handoff_card(item)
    write_packets(queue)
    provider_packet_count = sum(len(item["provider_routes"]) for item in queue)
    estimated_cost = round(sum(item["estimated_external_cost_usd"] for item in queue), 3)
    ready = (
        producer_package.get("decision") == "packaged_for_internal_producer_demo"
        and director_review.get("decision") == "conditional_pass_for_internal_producer_demo"
        and bool(queue)
    )
    manifest = {
        "task_id": task_id,
        "stage": "high_quality_polish_queue",
        "decision": "handoff_queue_ready_not_submitted" if ready else "handoff_queue_needs_review",
        "final_release_ready": False,
        "source_director_review": rel(DIRECTOR_REVIEW_PATH) if DIRECTOR_REVIEW_PATH.exists() else "",
        "source_producer_package": rel(PRODUCER_PACKAGE_PATH) if PRODUCER_PACKAGE_PATH.exists() else "",
        "provider_registry": rel(PROVIDER_REGISTRY_PATH) if PROVIDER_REGISTRY_PATH.exists() else "",
        "registry_provider_count": len(provider_registry.get("providers", {})),
        "queue_count": len(queue),
        "provider_packet_count": provider_packet_count,
        "estimated_external_cost_usd": estimated_cost,
        "provider_packets": rel(PACKET_PATH),
        "queue": queue,
        "submit_gate": {
            "allowed_provider_count": submit_gate.get("allowed_provider_count", 0),
            "blocked_provider_count": submit_gate.get("blocked_provider_count", 0),
            "total_estimated_cost_usd": submit_gate.get("total_estimated_cost_usd", 0),
            "approval_request": submit_gate.get("approval_request", ""),
        },
        "report": rel(REPORT_PATH),
        "next_step": "Configure one provider credential/cost cap or run local Remotion/ComfyUI polish tests for selected queue items.",
    }
    write_json(MANIFEST_PATH, manifest)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-HQ-POLISH-QUEUE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_queue(args.task_id)
    if args.quiet:
        print(rel(MANIFEST_PATH))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
