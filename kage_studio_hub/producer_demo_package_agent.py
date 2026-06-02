from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
DELIVERABLES_DIR = ANIME_PROJECT / "deliverables"
PACKAGE_DIR = DELIVERABLES_DIR / "producer_demo_v01"

MASTER_VIDEO = ANIME_PROJECT / "episode_segments" / "master_preview" / "final" / "kage_preview_with_replacements.mp4"
PACKAGE_MANIFEST = PACKAGE_DIR / "producer_demo_manifest.json"
PACKAGE_REPORT = PACKAGE_DIR / "README_PRODUCER_DEMO.md"
PACKAGE_ZIP = DELIVERABLES_DIR / "producer_demo_v01.zip"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_artifact(source: Path, target_relative: str, role: str, required: bool = True) -> dict:
    target = PACKAGE_DIR / target_relative
    exists = source.exists()
    if exists:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if required and not exists:
        raise FileNotFoundError(source)
    return {
        "role": role,
        "source": rel(source) if exists else str(source),
        "package_path": rel(target),
        "exists": exists,
        "bytes": target.stat().st_size if target.exists() else 0,
    }


def copy_keyframes(director_review: dict) -> list[dict]:
    copied = []
    contact_sheet = director_review.get("contact_sheet", "")
    if contact_sheet:
        copied.append(copy_artifact(WORKSPACE / contact_sheet, "review/keyframes/master_review_contact_sheet.png", "contact_sheet"))
    for item in director_review.get("keyframes", []):
        frame = item.get("frame", "")
        if not frame:
            continue
        frame_source = WORKSPACE / frame
        frame_name = f"{item.get('segment', 'segment')}_{item.get('shot_id', 'shot')}.png".replace("/", "_")
        copied.append(copy_artifact(frame_source, f"review/keyframes/{frame_name}", f"keyframe:{item.get('shot_id', '')}"))
    return copied


def build_readme(manifest: dict) -> str:
    lines = [
        "# Producer Demo Package v01",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        "",
        "## Main Playback",
        "",
        "- `video/kage_preview_with_replacements.mp4` is the current reviewed master preview.",
        "- Specs verified upstream: 1920x1080, 24fps, H.264 video with AAC temp audio, about 184 seconds.",
        "",
        "## Review State",
        "",
        f"- Master acceptance: {manifest['acceptance']['decision']} ({manifest['acceptance']['passed_count']} checks passed, {manifest['acceptance']['failed_count']} failed).",
        f"- Director/risk review: {manifest['director_review']['decision']} ({manifest['director_review']['nonblank_keyframe_count']}/{manifest['director_review']['reviewed_keyframe_count']} keyframes nonblank).",
        "- Final release ready: false. This is an internal producer demo package, not a locked release master.",
        "",
        "## Contents",
        "",
        "| Role | Package File | Bytes |",
        "| --- | --- | ---: |",
    ]
    for item in manifest["artifacts"]:
        lines.append(f"| {item['role']} | {item['package_path']} | {item['bytes']} |")
    lines.extend(
        [
            "",
            "## Next Production Step",
            "",
            "Use this package for producer/director review, then choose one of two routes: approve as internal demo, or send the marked shots to high-quality external/video-model providers after credentials, budget caps, and producer approval are configured.",
        ]
    )
    return "\n".join(lines)


def zip_package() -> dict:
    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACKAGE_DIR))
    return {"path": rel(PACKAGE_ZIP), "exists": PACKAGE_ZIP.exists(), "bytes": PACKAGE_ZIP.stat().st_size}


def run_package(task_id: str) -> dict:
    acceptance = load_json(PIPELINE_DIR / "acceptance" / "master_acceptance_manifest.json", {})
    director_review = load_json(PIPELINE_DIR / "director_review" / "director_risk_review_manifest.json", {})
    external_review = load_json(PIPELINE_DIR / "external_reviews" / "approved_external_results.json", {})
    replacements = load_json(PIPELINE_DIR / "replacements" / "candidate_manifest.json", {})
    provider_registry = PIPELINE_DIR / "provider_registry.json"
    submit_gate = PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json"

    artifacts = [
        copy_artifact(MASTER_VIDEO, "video/kage_preview_with_replacements.mp4", "master_preview_video"),
        copy_artifact(PIPELINE_DIR / "acceptance" / "master_acceptance_report.md", "reports/master_acceptance_report.md", "master_acceptance_report"),
        copy_artifact(PIPELINE_DIR / "acceptance" / "master_acceptance_manifest.json", "manifests/master_acceptance_manifest.json", "master_acceptance_manifest"),
        copy_artifact(PIPELINE_DIR / "director_review" / "director_risk_review.md", "reports/director_risk_review.md", "director_risk_review_report"),
        copy_artifact(PIPELINE_DIR / "director_review" / "director_risk_review_manifest.json", "manifests/director_risk_review_manifest.json", "director_risk_review_manifest"),
        copy_artifact(PIPELINE_DIR / "external_reviews" / "external_result_review.md", "reports/external_result_review.md", "external_result_review_report"),
        copy_artifact(PIPELINE_DIR / "external_reviews" / "approved_external_results.json", "manifests/approved_external_results.json", "approved_external_results_manifest"),
        copy_artifact(PIPELINE_DIR / "replacements" / "candidate_manifest.json", "manifests/replacement_candidate_manifest.json", "replacement_candidate_manifest"),
        copy_artifact(ANIME_PROJECT / "EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md", "docs/EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md", "external_video_runbook"),
        copy_artifact(provider_registry, "manifests/provider_registry.json", "provider_registry"),
        copy_artifact(submit_gate, "manifests/external_submit_gate_manifest.json", "external_submit_gate_manifest"),
    ]
    artifacts.extend(copy_keyframes(director_review))

    acceptance_summary = {
        "decision": acceptance.get("decision", "not_run"),
        "passed_count": acceptance.get("checklist", {}).get("passed_count", 0),
        "failed_count": acceptance.get("checklist", {}).get("failed_count", 0),
    }
    director_summary = {
        "decision": director_review.get("decision", "not_run"),
        "reviewed_keyframe_count": director_review.get("reviewed_keyframe_count", 0),
        "nonblank_keyframe_count": director_review.get("nonblank_keyframe_count", 0),
    }
    all_required_present = all(item["exists"] and item["bytes"] > 0 for item in artifacts)
    decision = (
        "packaged_for_internal_producer_demo"
        if all_required_present
        and acceptance_summary["decision"] == "ready_for_director_producer_review"
        and director_summary["decision"] == "conditional_pass_for_internal_producer_demo"
        else "package_needs_repair"
    )
    manifest = {
        "task_id": task_id,
        "stage": "producer_demo_package",
        "decision": decision,
        "final_release_ready": False,
        "package_dir": rel(PACKAGE_DIR),
        "zip": {},
        "master_video": rel(MASTER_VIDEO),
        "acceptance": acceptance_summary,
        "director_review": director_summary,
        "external_reviews": {
            "reviewed_count": external_review.get("reviewed_count", 0),
            "approved_count": external_review.get("approved_count", 0),
            "returned_count": external_review.get("returned_count", 0),
        },
        "replacements": {
            "mode": replacements.get("mode", ""),
            "replacement_count": replacements.get("replacement_count", 0),
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "readme": rel(PACKAGE_REPORT),
        "next_step": "Producer review can approve this package for internal demo use or request high-quality provider replacement on selected shots.",
    }
    PACKAGE_REPORT.write_text(build_readme(manifest), encoding="utf-8")
    manifest["artifacts"].append(
        {
            "role": "producer_demo_readme",
            "source": rel(PACKAGE_REPORT),
            "package_path": rel(PACKAGE_REPORT),
            "exists": PACKAGE_REPORT.exists(),
            "bytes": PACKAGE_REPORT.stat().st_size,
        }
    )
    manifest_artifact = {
        "role": "producer_demo_manifest",
        "source": rel(PACKAGE_MANIFEST),
        "package_path": rel(PACKAGE_MANIFEST),
        "exists": True,
        "bytes": 0,
    }
    manifest["artifacts"].append(manifest_artifact)
    manifest["artifact_count"] = len(manifest["artifacts"])
    write_json(PACKAGE_MANIFEST, manifest)
    manifest_artifact["bytes"] = PACKAGE_MANIFEST.stat().st_size
    write_json(PACKAGE_MANIFEST, manifest)
    manifest["zip"] = zip_package()
    write_json(PACKAGE_MANIFEST, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-PRODUCER-DEMO-PACKAGE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_package(args.task_id)
    if args.quiet:
        print(rel(PACKAGE_MANIFEST))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
