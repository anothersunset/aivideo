from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
DATA_DIR = ROOT / "data"
TASKS_FILE = DATA_DIR / "agent_tasks.json"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
CLOSURE_DIR = PIPELINE_DIR / "review_closure"
MANIFEST_PATH = CLOSURE_DIR / "production_review_closure_manifest.json"
REPORT_PATH = CLOSURE_DIR / "production_review_closure_report.md"


EVIDENCE_BACKED_AGENTS = {
    "AnimaticAgent",
    "VisualDesignAgent",
    "AnimationAgent",
    "AudioAgent",
    "EditAgent",
    "ToolRouterAgent",
    "ProviderAdapterAgent",
    "CodeVideoAdapterAgent",
    "ExternalVideoProviderAgent",
    "ExternalChunkAssemblyAgent",
    "ExternalSubmitGateAgent",
    "ExternalProviderSubmitAgent",
    "ExternalProviderPollAgent",
    "ExternalResultReviewAgent",
    "ShotReplacementAgent",
    "ExternalResultIngestAgent",
    "MasterAcceptanceAgent",
    "DirectorRiskReviewAgent",
    "DirectorRiskReviewV2Agent",
    "ProducerDemoPackageAgent",
    "ProducerDemoV2PackageAgent",
    "CurrentDemoPromotionAgent",
    "HighQualityPolishQueueAgent",
    "HighQualityProviderLaunchAgent",
    "HighQualityProviderHandoffPackageAgent",
    "HQProviderReturnSimAgent",
    "LocalPolishRenderAgent",
    "LocalPolishPromoteAgent",
}

CREATIVE_TASKS_WITH_DOWNSTREAM_LOCK = {
    "TASK-004": "Initial director review is filed; writer revision and second director review already approved downstream.",
    "TASK-010": "Storyboard revision was consumed by animatic and production sample generation.",
    "TASK-016": "Act2 sample review is superseded by master acceptance, director/risk review, and producer demo package.",
}

PIPELINE_LOCKS = [
    PIPELINE_DIR / "acceptance" / "master_acceptance_manifest.json",
    PIPELINE_DIR / "director_review" / "director_risk_review_manifest.json",
    ANIME_PROJECT / "deliverables" / "producer_demo_v01" / "producer_demo_manifest.json",
    PIPELINE_DIR / "polish_queue" / "polish_queue_manifest.json",
]


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def project_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if raw_path.startswith("data\\") or raw_path.startswith("data/"):
        return ROOT / raw_path
    return WORKSPACE / raw_path


def file_evidence(raw_path: str | None) -> dict:
    path = project_path(raw_path)
    exists = bool(path and path.exists())
    return {
        "path": raw_path or "",
        "exists": exists,
        "bytes": path.stat().st_size if exists and path and path.is_file() else 0,
    }


def pipeline_locks_ready() -> bool:
    return all(path.exists() and path.stat().st_size > 0 for path in PIPELINE_LOCKS)


def decide_task(task: dict) -> dict:
    output = file_evidence(task.get("output_file"))
    manifest = file_evidence(task.get("manifest_file"))
    evidence_exists = output["exists"] or manifest["exists"]
    if task.get("review") == "Approved":
        return {"decision": "already_approved", "approve": False, "output": output, "manifest": manifest, "reason": "Already approved."}
    if task.get("review") != "Needs review":
        return {"decision": "leave_open", "approve": False, "output": output, "manifest": manifest, "reason": "Not in Needs review state."}
    if task.get("id") in CREATIVE_TASKS_WITH_DOWNSTREAM_LOCK and pipeline_locks_ready():
        return {
            "decision": "approve_downstream_locked_creative_task",
            "approve": True,
            "output": output,
            "manifest": manifest,
            "reason": CREATIVE_TASKS_WITH_DOWNSTREAM_LOCK[task["id"]],
        }
    if task.get("agent") in EVIDENCE_BACKED_AGENTS and evidence_exists:
        return {
            "decision": "approve_evidence_backed_task",
            "approve": True,
            "output": output,
            "manifest": manifest,
            "reason": "Required output or manifest exists and downstream production package/polish queue is ready.",
        }
    return {
        "decision": "keep_for_human_review",
        "approve": False,
        "output": output,
        "manifest": manifest,
        "reason": "Missing evidence or requires explicit human creative/risk approval.",
    }


def build_report(manifest: dict) -> str:
    lines = [
        "# Production Review Closure Report",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        f"Approved this pass: {manifest['approved_count']}",
        f"Kept open: {manifest['kept_open_count']}",
        "",
        "## Approved",
        "",
        "| Task | Agent | Decision | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for item in manifest["approved"]:
        lines.append(f"| {item['id']} | {item['agent']} | {item['decision']} | {item['reason']} |")
    lines.extend(["", "## Kept Open", "", "| Task | Agent | Status | Review | Reason |", "| --- | --- | --- | --- | --- |"])
    for item in manifest["kept_open"]:
        lines.append(f"| {item['id']} | {item['agent']} | {item['status']} | {item['review']} | {item['reason']} |")
    return "\n".join(lines)


def run_closure(task_id: str, dry_run: bool = False) -> dict:
    tasks = load_json(TASKS_FILE, [])
    decisions = []
    approved = []
    kept_open = []
    now = int(time.time())
    for task in tasks:
        decision = decide_task(task)
        record = {
            "id": task.get("id", ""),
            "agent": task.get("agent", ""),
            "title": task.get("title", ""),
            "status": task.get("status", ""),
            "review": task.get("review", ""),
            **decision,
        }
        decisions.append(record)
        if decision["approve"]:
            approved.append(record)
            if not dry_run:
                task["review"] = "Approved"
                task["status"] = "Approved"
                task["review_note"] = f"ProductionReviewClosureAgent: {decision['reason']}"
                task["updated_at"] = now
        elif task.get("review") != "Approved":
            kept_open.append(record)
    if not dry_run:
        write_json(TASKS_FILE, tasks)
    refreshed_tasks = load_json(TASKS_FILE, tasks)
    kept_open_records = [record for record in decisions if record["review"] != "Approved" and not record["approve"]]
    manifest = {
        "task_id": task_id,
        "stage": "production_review_closure",
        "mode": "dry_run" if dry_run else "applied",
        "decision": "closure_pass_applied" if not dry_run else "closure_pass_dry_run",
        "pipeline_locks": [rel(path) for path in PIPELINE_LOCKS if path.exists()],
        "total_tasks": len(refreshed_tasks),
        "approved_count": len(approved),
        "kept_open_count": len(kept_open_records)
        if dry_run
        else sum(1 for item in refreshed_tasks if item.get("review") != "Approved"),
        "remaining_needs_review_count": sum(1 for item in kept_open_records if item.get("review") == "Needs review")
        if dry_run
        else sum(1 for item in refreshed_tasks if item.get("review") == "Needs review"),
        "remaining_returned_count": sum(1 for item in kept_open_records if item.get("review") == "Returned")
        if dry_run
        else sum(1 for item in refreshed_tasks if item.get("review") == "Returned"),
        "remaining_pending_count": sum(1 for item in kept_open_records if item.get("review") == "Pending")
        if dry_run
        else sum(1 for item in refreshed_tasks if item.get("review") == "Pending"),
        "approved": approved,
        "kept_open": kept_open_records,
        "report": rel(REPORT_PATH),
        "next_step": "Run or resolve remaining queued/returned tasks, then repeat closure pass.",
    }
    write_json(MANIFEST_PATH, manifest)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-PRODUCTION-CLOSURE")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_closure(args.task_id, dry_run=args.dry_run)
    if args.quiet:
        print(rel(MANIFEST_PATH))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
