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
PACKAGE_DIR = DELIVERABLES_DIR / "producer_demo_v02"

MASTER_VIDEO = ANIME_PROJECT / "episode_segments" / "master_preview" / "final" / "kage_preview_with_local_polish.mp4"
MASTER_MANIFEST = ANIME_PROJECT / "episode_segments" / "master_preview" / "manifest_with_local_polish.json"
PACKAGE_MANIFEST = PACKAGE_DIR / "producer_demo_v02_manifest.json"
PACKAGE_REPORT = PACKAGE_DIR / "README_PRODUCER_DEMO_V02.md"
PACKAGE_ZIP = DELIVERABLES_DIR / "producer_demo_v02.zip"
LOCAL_POLISH_DIR = PIPELINE_DIR / "polish_outputs" / "local_remotion"
PROMOTION_DIR = LOCAL_POLISH_DIR / "promotion"


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


def copy_segment_manifests(master_manifest: dict) -> list[dict]:
    artifacts = []
    for item in master_manifest.get("segment_manifests", []):
        source = WORKSPACE / item
        segment_name = source.parent.name
        artifacts.append(
            copy_artifact(
                source,
                f"manifests/segments/{segment_name}_{source.name}",
                f"segment_manifest:{segment_name}",
            )
        )
    return artifacts


def build_readme(manifest: dict) -> str:
    lines = [
        "# Producer Demo Package v02",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        "",
        "## Main Playback",
        "",
        "- `video/kage_preview_with_local_polish.mp4` is the current local-polish master preview.",
        "- Specs verified in this package: 1920x1080, 24fps, H.264 video with AAC temp audio, about 184 seconds.",
        "- This is still an internal producer demo, not a final release master.",
        "",
        "## What Changed Since v01",
        "",
        f"- Promoted local polish shots: {manifest['local_polish_promotion']['promoted_count']}.",
        f"- Director/risk v02 review: {manifest['director_review_v02']['decision']} ({manifest['director_review_v02']['nonblank_keyframe_count']}/{manifest['director_review_v02']['reviewed_keyframe_count']} keyframes nonblank).",
        "- The promoted version keeps the previous multi-segment edit structure and adds versioned manifests instead of overwriting v01.",
        "- Included evidence: local polish render manifest, promotion manifest, v02 director/risk review, contact sheets, and segment manifests.",
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
            "Run director/risk review against v02, then either approve this as the current product demo or send the promoted shots to configured external providers for a higher-quality pass.",
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
    master_manifest = load_json(MASTER_MANIFEST, {})
    render_manifest = load_json(LOCAL_POLISH_DIR / "local_polish_render_manifest.json", {})
    promotion_manifest = load_json(PROMOTION_DIR / "local_polish_promotion_manifest.json", {})
    director_review_v02 = load_json(PIPELINE_DIR / "director_review_v02" / "director_risk_review_v02_manifest.json", {})
    submit_gate = PIPELINE_DIR / "submit_gate" / "external_submit_gate_manifest.json"

    artifacts = [
        copy_artifact(MASTER_VIDEO, "video/kage_preview_with_local_polish.mp4", "master_preview_video"),
        copy_artifact(MASTER_MANIFEST, "manifests/manifest_with_local_polish.json", "master_manifest"),
        copy_artifact(LOCAL_POLISH_DIR / "local_polish_render_manifest.json", "manifests/local_polish_render_manifest.json", "local_polish_render_manifest"),
        copy_artifact(LOCAL_POLISH_DIR / "local_polish_render_report.md", "reports/local_polish_render_report.md", "local_polish_render_report"),
        copy_artifact(PROMOTION_DIR / "local_polish_promotion_manifest.json", "manifests/local_polish_promotion_manifest.json", "local_polish_promotion_manifest"),
        copy_artifact(PROMOTION_DIR / "local_polish_promotion_report.md", "reports/local_polish_promotion_report.md", "local_polish_promotion_report"),
        copy_artifact(PIPELINE_DIR / "director_review_v02" / "director_risk_review_v02_manifest.json", "manifests/director_risk_review_v02_manifest.json", "director_risk_review_v02_manifest"),
        copy_artifact(PIPELINE_DIR / "director_review_v02" / "director_risk_review_v02.md", "reports/director_risk_review_v02.md", "director_risk_review_v02_report"),
        copy_artifact(PIPELINE_DIR / "director_review_v02" / "keyframes" / "v02_master_review_contact_sheet.png", "review/keyframes/v02_master_review_contact_sheet.png", "director_risk_review_v02_contact_sheet"),
        copy_artifact(LOCAL_POLISH_DIR / "review_frames" / "local_polish_contact_sheet.png", "review/keyframes/local_polish_contact_sheet.png", "local_polish_contact_sheet"),
        copy_artifact(PROMOTION_DIR / "review_frames" / "local_polish_master_contact_sheet.png", "review/keyframes/local_polish_master_contact_sheet.png", "local_polish_master_contact_sheet"),
        copy_artifact(PIPELINE_DIR / "provider_registry.json", "manifests/provider_registry.json", "provider_registry"),
        copy_artifact(submit_gate, "manifests/external_submit_gate_manifest.json", "external_submit_gate_manifest"),
        copy_artifact(ANIME_PROJECT / "EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md", "docs/EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md", "external_video_runbook"),
    ]
    artifacts.extend(copy_segment_manifests(master_manifest))

    all_required_present = all(item["exists"] and item["bytes"] > 0 for item in artifacts)
    review_passed = director_review_v02.get("decision") == "conditional_pass_for_local_polish_producer_demo_v02"
    decision = "packaged_for_reviewed_local_polish_producer_demo_v02" if all_required_present and review_passed else "package_needs_repair"
    manifest = {
        "task_id": task_id,
        "stage": "producer_demo_package_v02",
        "decision": decision,
        "final_release_ready": False,
        "package_dir": rel(PACKAGE_DIR),
        "zip": {},
        "master_video": rel(MASTER_VIDEO),
        "master_manifest": rel(MASTER_MANIFEST),
        "master": {
            "shot_count": master_manifest.get("shot_count", 0),
            "duration_seconds": master_manifest.get("duration_seconds", 0),
        },
        "local_polish": {
            "rendered_count": render_manifest.get("rendered_count", 0),
            "accepted_count": render_manifest.get("accepted_count", 0),
            "rejected_count": render_manifest.get("rejected_count", 0),
        },
        "local_polish_promotion": {
            "decision": promotion_manifest.get("decision", "not_run"),
            "promoted_count": promotion_manifest.get("promoted_count", 0),
            "segments": promotion_manifest.get("segments", []),
        },
        "director_review_v02": {
            "decision": director_review_v02.get("decision", "not_run"),
            "reviewed_keyframe_count": director_review_v02.get("reviewed_keyframe_count", 0),
            "nonblank_keyframe_count": director_review_v02.get("nonblank_keyframe_count", 0),
            "replacement_keyframe_count": director_review_v02.get("replacement_keyframe_count", 0),
            "risk_keyframe_count": director_review_v02.get("risk_keyframe_count", 0),
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "readme": rel(PACKAGE_REPORT),
        "next_step": "Run director/risk review against v02 and then decide whether this is the current producer demo or needs external high-quality polish.",
    }
    PACKAGE_REPORT.write_text(build_readme(manifest), encoding="utf-8")
    manifest["artifacts"].append(
        {
            "role": "producer_demo_v02_readme",
            "source": rel(PACKAGE_REPORT),
            "package_path": rel(PACKAGE_REPORT),
            "exists": PACKAGE_REPORT.exists(),
            "bytes": PACKAGE_REPORT.stat().st_size,
        }
    )
    manifest_artifact = {
        "role": "producer_demo_v02_manifest",
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
    parser.add_argument("--task-id", default="TASK-PRODUCER-DEMO-V02-PACKAGE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_package(args.task_id)
    if args.quiet:
        print(rel(PACKAGE_MANIFEST))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
