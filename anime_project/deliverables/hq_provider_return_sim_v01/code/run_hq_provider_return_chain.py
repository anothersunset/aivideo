#!/usr/bin/env python3
"""TASK-058 -> TASK-061 orchestrator: simulated HQ provider return replacement chain.

Runs the Codex-paused chain end to end in SIMULATION mode and enforces every
acceptance gate. NO external provider call, NO HTTP submit/poll, NO API key, NO
secret. The final master preview is kept at needs_director_review.

Stages:
  TASK-058  hq_provider_return_sim_agent.py   -> simulated inbox MP4s + manifest
  TASK-059  external_result_ingest_agent.py   -> validated_external_results.json
  TASK-060  external_result_review_agent.py   -> approved_external_results.json
  TASK-061  shot_replacement_agent.py         -> master preview with replacements

This script only ORCHESTRATES the existing agents; it must run in an environment
that has Python + FFmpeg installed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent            # kage_studio_hub
WORKSPACE = ROOT.parent
ANIME = WORKSPACE / "anime_project"
PIPE = ANIME / "pipeline"
EXTERNAL = PIPE / "external_results"
MANIFEST_DIR = EXTERNAL / "manifests"
REVIEW_DIR = PIPE / "external_reviews"
SEGMENT_DIR = ANIME / "episode_segments"
SIM_MANIFEST = MANIFEST_DIR / "simulated_hq_provider_returns.json"
HUB_SIM_MANIFEST = PIPE / "provider_returns" / "current_demo_hq_v01" / "hq_provider_return_sim_manifest.json"
HUB_SIM_REPORT = PIPE / "provider_returns" / "current_demo_hq_v01" / "hq_provider_return_sim_report.md"
LAUNCH_MANIFEST = PIPE / "provider_launch" / "current_demo_hq_v01" / "high_quality_provider_launch_manifest.json"
VALIDATED_MANIFEST = MANIFEST_DIR / "validated_external_results.json"
REVIEW_MANIFEST = REVIEW_DIR / "approved_external_results.json"
REVIEW_REPORT = REVIEW_DIR / "external_result_review.md"
MASTER_MANIFEST = SEGMENT_DIR / "master_preview" / "manifest_with_replacements.json"
MASTER_VIDEO = SEGMENT_DIR / "master_preview" / "final" / "kage_preview_with_replacements.mp4"
TASKS_PATH = ROOT / "data" / "agent_tasks.json"

PY = sys.executable or "python"


class GateError(RuntimeError):
    pass


def run(script: str, *args: str) -> None:
    cmd = [PY, str(ROOT / script), *args]
    print(f"\n=== run: {' '.join(cmd)} ===")
    subprocess.run(cmd, check=True, cwd=str(WORKSPACE))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel_win(path: Path) -> str:
    return str(path.relative_to(WORKSPACE)).replace("/", "\\")


def stage_058() -> None:
    run("hq_provider_return_sim_agent.py", "--task-id", "TASK-058", "--quiet")
    m = load_json(SIM_MANIFEST)
    expected = int(load_json(LAUNCH_MANIFEST).get("selected_shot_count", 0) or 0)
    if m.get("external_api_called") is not False:
        raise GateError("TASK-058: external_api_called must be false")
    if m.get("mode") != "simulated_provider_return_no_external_api_call":
        raise GateError("TASK-058: mode flag mismatch")
    if expected and m.get("return_count", 0) != expected:
        raise GateError(f"TASK-058: return_count={m.get('return_count')} expected={expected}")
    print(f"[058] OK return_count={m.get('return_count')}")


def stage_059() -> None:
    run("external_result_ingest_agent.py", "--mode", "scan", "--quiet")
    m = load_json(VALIDATED_MANIFEST)
    expected = int(load_json(LAUNCH_MANIFEST).get("selected_shot_count", 0) or 0)
    if m.get("accepted_count", 0) < expected:
        raise GateError(f"TASK-059: accepted_count={m.get('accepted_count')} (<{expected})")
    if m.get("rejected_count", 0) != 0:
        raise GateError(f"TASK-059: rejected_count={m.get('rejected_count')} (!=0)")
    if m.get("unknown_count", 0) != 0:
        raise GateError(f"TASK-059: unknown_count={m.get('unknown_count')} (!=0)")
    print(f"[059] OK accepted={m.get('accepted_count')} rejected=0 unknown=0")


def stage_060() -> None:
    run("external_result_review_agent.py", "--task-id", "TASK-060", "--quiet")
    m = load_json(REVIEW_MANIFEST)
    expected = int(load_json(LAUNCH_MANIFEST).get("selected_shot_count", 0) or 0)
    if m.get("reviewed_count", 0) < expected:
        raise GateError(f"TASK-060: reviewed_count={m.get('reviewed_count')} (<{expected})")
    if m.get("approved_count", 0) < expected:
        raise GateError(f"TASK-060: approved_count={m.get('approved_count')} (<{expected})")
    if m.get("returned_count", 0) != 0:
        raise GateError(f"TASK-060: returned_count={m.get('returned_count')} (!=0)")
    print(f"[060] OK reviewed={m.get('reviewed_count')} approved={m.get('approved_count')} returned=0")


def stage_061() -> None:
    run("shot_replacement_agent.py", "--stage", "all", "--task-id", "TASK-061", "--quiet")
    m = load_json(MASTER_MANIFEST)
    status = m.get("status")
    if status != "needs_director_review":
        m["status"] = "needs_director_review"
        MASTER_MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[guard] master status was '{status}', forced back to needs_director_review")
    print("[061] OK master_preview status=needs_director_review")


def update_agent_tasks() -> None:
    now = int(time.time())
    defs = [
        {
            "id": "TASK-058", "agent": "HQProviderReturnSimAgent",
            "title": "Simulate HQ provider returns for current-demo launch rows",
            "prompt": "Generate simulated HQ provider-return MP4s for all current-demo launch rows into the external_results inbox. No external API call.",
            "status": "Approved", "review": "Approved",
            "manifest_file": rel_win(HUB_SIM_MANIFEST), "output_file": rel_win(HUB_SIM_REPORT),
            "output": "Simulated provider returns generated for current-demo launch rows into external_results inbox.",
            "review_note": "HQ provider return simulation completed; no external API call.",
        },
        {
            "id": "TASK-059", "agent": "ExternalResultIngestAgent",
            "title": "Ingest and validate simulated provider returns",
            "prompt": "Scan the external_results inbox and validate simulated returns (1920x1080 / 24fps / duration-close / non-empty).",
            "status": "Approved", "review": "Approved",
            "manifest_file": rel_win(VALIDATED_MANIFEST), "output_file": "",
            "output": "Validated external results: accepted>=2, rejected=0, unknown=0.",
            "review_note": "Simulated provider returns ingested and validated.",
        },
        {
            "id": "TASK-060", "agent": "ExternalResultReviewAgent",
            "title": "Review accepted simulated returns",
            "prompt": "Review accepted simulated returns, extract review frames, attach risk rules, and approve for replacement.",
            "status": "Approved", "review": "Approved",
            "manifest_file": rel_win(REVIEW_MANIFEST), "output_file": rel_win(REVIEW_REPORT),
            "output": "External review approved the accepted simulated returns.",
            "review_note": "Accepted simulated returns reviewed and approved for replacement workflow.",
        },
        {
            "id": "TASK-061", "agent": "ShotReplacementAgent",
            "title": "Apply replacements and rebuild master preview",
            "prompt": "Promote approved returns into replacement manifests, re-edit segments, and rebuild the master preview.",
            "status": "Approved", "review": "Approved",
            "manifest_file": rel_win(MASTER_MANIFEST), "output_file": rel_win(MASTER_VIDEO),
            "output": "Master preview rebuilt with replacements; status needs_director_review.",
            "review_note": "Replacement workflow completed; master preview requires director review before final release.",
        },
    ]
    tasks = load_json(TASKS_PATH)
    by_id = {t.get("id"): t for t in tasks}
    for d in defs:
        rec = by_id.get(d["id"])
        if rec is None:
            rec = {"id": d["id"], "created_at": now}
            tasks.append(rec)
            by_id[d["id"]] = rec
        rec.update({
            "agent": d["agent"], "title": d["title"], "prompt": d["prompt"],
            "status": d["status"], "priority": "High", "review": d["review"],
            "output": d["output"], "manifest_file": d["manifest_file"],
            "review_note": d["review_note"], "updated_at": now,
        })
        if d.get("output_file"):
            rec["output_file"] = d["output_file"]
    TASKS_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[tasks] agent_tasks.json updated for TASK-058..061")


def self_check() -> None:
    sim = load_json(SIM_MANIFEST)
    assert sim.get("external_api_called") is False, "sim manifest must declare external_api_called=false"
    assert sim.get("mode") == "simulated_provider_return_no_external_api_call"
    master = load_json(MASTER_MANIFEST)
    assert master.get("status") == "needs_director_review", "master must stay needs_director_review"
    print("[self-check] guardrails OK: simulated, no external API, needs_director_review")


def main() -> None:
    stage_058()
    stage_059()
    stage_060()
    stage_061()
    update_agent_tasks()
    self_check()
    print("\nDONE: TASK-058..061 simulated chain complete; master preview = needs_director_review")


if __name__ == "__main__":
    main()
