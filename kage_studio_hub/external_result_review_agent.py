from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_common import resolve_workspace_path, run_checked


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
EXTERNAL_RESULTS_DIR = PIPELINE_DIR / "external_results"
VALIDATED_RESULTS_PATH = EXTERNAL_RESULTS_DIR / "manifests" / "validated_external_results.json"
REVIEW_DIR = PIPELINE_DIR / "external_reviews"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ffprobe_frames(path: Path) -> int:
    result = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_frames",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(path),
        ],
        cwd=str(WORKSPACE),
        capture_text=True,
    )
    raw = result.stdout.strip()
    return int(raw) if raw.isdigit() else 0


def extract_review_frame(item: dict) -> str:
    source = resolve_workspace_path(WORKSPACE, item["path"])
    frame_dir = REVIEW_DIR / "frames" / item["provider"] / item["segment"] / item["shot_id"]
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_path = frame_dir / f"{item['shot_id']}_{item['provider']}_mid.png"
    midpoint = max(0.0, float(item.get("actual_duration_seconds", 0) or 0) / 2)
    run_checked(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{midpoint:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(frame_path),
        ],
        cwd=str(WORKSPACE),
    )
    return rel(frame_path)


def risk_rules_for(item: dict) -> list[str]:
    shot_id = item.get("shot_id", "")
    rules = [
        "Maintain original project identity; do not copy protected compositions or character designs.",
        "Keep violence readable but restrained for international cut options.",
        "Returned video must preserve duration, resolution, and provider traceability.",
    ]
    if shot_id == "08-003":
        rules.append("08-003 must not show face or pain expression.")
    if shot_id == "11-004":
        rules.append("11-004 parasite count limit: 8.")
    if shot_id in {"12-001", "12-002", "12-003"}:
        rules.append("Child-harm-adjacent shots must use props, hands, and silence instead of pain-process depiction.")
    return rules


def review_item(item: dict, task_id: str) -> dict:
    source = resolve_workspace_path(WORKSPACE, item["path"])
    frame_count = ffprobe_frames(source)
    frame_path = extract_review_frame(item)
    technical_checks = item.get("checks", {})
    technical_pass = bool(item.get("accepted")) and all(bool(value) for value in technical_checks.values())
    traceable = bool(item.get("provider") and item.get("path") and source.exists())
    risk_rules = risk_rules_for(item)
    approved = technical_pass and traceable
    review_notes = [
        "technical checks passed" if technical_pass else "technical checks need repair",
        "provider route traceable" if traceable else "provider route missing",
        "mid-frame extracted for director review",
        "risk rules attached for final human review",
    ]
    return {
        "task_id": task_id,
        "provider": item["provider"],
        "segment": item["segment"],
        "shot_id": item["shot_id"],
        "path": item["path"],
        "duration_seconds": item["actual_duration_seconds"],
        "expected_duration_seconds": item["expected_duration_seconds"],
        "frame_count": frame_count,
        "review_frame": frame_path,
        "risk_rules": risk_rules,
        "technical_checks": technical_checks,
        "approved": approved,
        "status": "approved_for_replacement" if approved else "returned_for_repair",
        "review_notes": review_notes,
    }


def run_review(task_id: str) -> dict:
    validated = load_json(VALIDATED_RESULTS_PATH, {})
    accepted = [item for item in validated.get("accepted_results", []) if item.get("accepted")]
    reviews = [review_item(item, task_id) for item in accepted]
    approved = [item for item in reviews if item["approved"]]
    returned = [item for item in reviews if not item["approved"]]
    report_lines = [
        "# External Result Review",
        "",
        f"Task: {task_id}",
        "",
        "| Provider | Segment | Shot | Decision | Review Frame |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in reviews:
        report_lines.append(
            f"| {item['provider']} | {item['segment']} | {item['shot_id']} | {item['status']} | {item['review_frame']} |"
        )
    manifest = {
        "task_id": task_id,
        "stage": "external_result_review",
        "source_manifest": rel(VALIDATED_RESULTS_PATH) if VALIDATED_RESULTS_PATH.exists() else "",
        "reviewed_count": len(reviews),
        "approved_count": len(approved),
        "returned_count": len(returned),
        "reviews": reviews,
        "approved_results": approved,
        "returned_results": returned,
        "report": rel(REVIEW_DIR / "external_result_review.md"),
        "next_step": "ShotReplacementAgent can promote approved_results into replacement manifests.",
    }
    write_json(REVIEW_DIR / "approved_external_results.json", manifest)
    (REVIEW_DIR / "external_result_review.md").write_text("\n".join(report_lines), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-EXTERNAL-REVIEW")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_review(args.task_id)
    output = REVIEW_DIR / "approved_external_results.json"
    if args.quiet:
        print(rel(output))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
