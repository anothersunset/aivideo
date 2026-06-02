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
LAUNCH_DIR = PIPELINE_DIR / "provider_launch" / "current_demo_hq_v01"
PACKAGE_DIR = DELIVERABLES_DIR / "provider_launch" / "current_demo_hq_v01"
PACKAGE_MANIFEST = PACKAGE_DIR / "current_demo_hq_provider_handoff_manifest.json"
PACKAGE_README = PACKAGE_DIR / "README_CURRENT_DEMO_HQ_PROVIDER_HANDOFF.md"
PACKAGE_ZIP = DELIVERABLES_DIR / "current_demo_hq_provider_handoff_v01.zip"
LAUNCH_MANIFEST = LAUNCH_DIR / "high_quality_provider_launch_manifest.json"
CURRENT_DEMO_MANIFEST = DELIVERABLES_DIR / "current_demo" / "current_demo_manifest.json"
CURRENT_DEMO_README = DELIVERABLES_DIR / "current_demo" / "CURRENT_PRODUCER_DEMO.md"


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


def unique_frame_artifacts(launch_manifest: dict) -> list[dict]:
    artifacts = []
    seen = set()
    for row in launch_manifest.get("launch_rows", []):
        raw = row.get("source_frame") or row.get("source_review_frame")
        if not raw or raw in seen:
            continue
        seen.add(raw)
        source = WORKSPACE / raw
        name = f"{row.get('queue_id', 'queue')}_{row.get('segment', 'segment')}_{row.get('shot_id', 'shot')}.png"
        artifacts.append(copy_artifact(source, f"keyframes/{name}", f"keyframe:{row.get('queue_id', '')}"))
    return artifacts


def provider_packet_artifacts(launch_manifest: dict) -> list[dict]:
    artifacts = []
    for packet in launch_manifest.get("provider_packets", []):
        source = WORKSPACE / packet.get("packet", "")
        provider = packet.get("provider", source.stem)
        artifacts.append(copy_artifact(source, f"providers/{provider}_launch_packet.json", f"provider_packet:{provider}"))
    return artifacts


def build_readme(manifest: dict) -> str:
    lines = [
        "# Current Demo HQ Provider Handoff v01",
        "",
        f"Task: {manifest['task_id']}",
        f"Decision: {manifest['decision']}",
        "",
        "## Purpose",
        "",
        "This package prepares the current internal demo for a first high-quality provider pass. It does not submit any external request.",
        "",
        "## Launch Summary",
        "",
        f"- Current demo version: {manifest['current_demo']['current_version']}",
        f"- Selected shots: {manifest['selected_shot_count']}",
        f"- Selected providers: {manifest['selected_provider_count']}",
        f"- Estimated first-pass cost: ${manifest['estimated_first_pass_cost_usd']}",
        f"- Submit status: {manifest['submit_status']}",
        "",
        "## Required Before Submit",
        "",
        "- Fill provider endpoint and token environment variables.",
        "- Set provider cost cap at or above the estimate.",
        "- Set provider submit approval to true only after producer/director approval.",
        "- Rerun ExternalSubmitGateAgent before ExternalProviderSubmitAgent.",
        "",
        "## Contents",
        "",
        "| Role | Package File | Bytes |",
        "| --- | --- | ---: |",
    ]
    for item in manifest["artifacts"]:
        lines.append(f"| {item['role']} | {item['package_path']} | {item['bytes']} |")
    lines.extend(["", "## Next Step", "", manifest["next_step"]])
    return "\n".join(lines)


def zip_package() -> dict:
    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACKAGE_DIR))
    with zipfile.ZipFile(PACKAGE_ZIP, "r") as archive:
        entry_count = len(archive.infolist())
    return {
        "path": rel(PACKAGE_ZIP),
        "exists": PACKAGE_ZIP.exists(),
        "bytes": PACKAGE_ZIP.stat().st_size,
        "entry_count": entry_count,
    }


def run_package(task_id: str) -> dict:
    launch = load_json(LAUNCH_MANIFEST, {})
    current_demo = load_json(CURRENT_DEMO_MANIFEST, {})
    if launch.get("decision") != "current_demo_hq_launch_ready_blocked_by_submit_gate":
        raise ValueError("HQ provider launch manifest is not ready")
    if current_demo.get("decision") != "producer_demo_v02_promoted_to_current_internal_demo":
        raise ValueError("current_demo is not promoted")

    artifacts = [
        copy_artifact(LAUNCH_MANIFEST, "manifests/high_quality_provider_launch_manifest.json", "launch_manifest"),
        copy_artifact(LAUNCH_DIR / "high_quality_provider_launch_report.md", "reports/high_quality_provider_launch_report.md", "launch_report"),
        copy_artifact(LAUNCH_DIR / "external_provider_config.current_demo_hq.template.json", "config/external_provider_config.current_demo_hq.template.json", "provider_config_template"),
        copy_artifact(LAUNCH_DIR / ".env.current_demo_hq.example", "config/.env.current_demo_hq.example", "env_example"),
        copy_artifact(LAUNCH_DIR / "selected_provider_launch_rows.jsonl", "manifests/selected_provider_launch_rows.jsonl", "selected_launch_rows"),
        copy_artifact(CURRENT_DEMO_MANIFEST, "current_demo/current_demo_manifest.json", "current_demo_manifest"),
        copy_artifact(CURRENT_DEMO_README, "current_demo/CURRENT_PRODUCER_DEMO.md", "current_demo_readme"),
    ]
    artifacts.extend(provider_packet_artifacts(launch))
    artifacts.extend(unique_frame_artifacts(launch))

    missing = [item for item in artifacts if not item["exists"] or item["bytes"] <= 0]
    manifest = {
        "task_id": task_id,
        "stage": "hq_provider_handoff_package",
        "decision": "current_demo_hq_provider_handoff_packaged",
        "submit_status": "not_submitted_blocked_by_submit_gate",
        "current_demo": {
            "manifest": rel(CURRENT_DEMO_MANIFEST),
            "current_version": current_demo.get("current_version", ""),
            "current_video": current_demo.get("current_video", ""),
            "current_zip": current_demo.get("current_zip", ""),
        },
        "launch_manifest": rel(LAUNCH_MANIFEST),
        "selected_shot_count": launch.get("selected_shot_count", 0),
        "selected_provider_count": launch.get("selected_provider_count", 0),
        "estimated_first_pass_cost_usd": launch.get("estimated_first_pass_cost_usd", 0),
        "provider_packets": launch.get("provider_packets", []),
        "artifact_count": len(artifacts),
        "missing_artifact_count": len(missing),
        "artifacts": artifacts,
        "readme": rel(PACKAGE_README),
        "zip": {},
        "next_step": "Configure provider credentials and cost cap, rerun ExternalSubmitGateAgent, then submit only the approved provider rows.",
    }
    PACKAGE_README.write_text(build_readme(manifest), encoding="utf-8")
    manifest["artifacts"].append(
        {
            "role": "handoff_readme",
            "source": rel(PACKAGE_README),
            "package_path": rel(PACKAGE_README),
            "exists": PACKAGE_README.exists(),
            "bytes": PACKAGE_README.stat().st_size,
        }
    )
    manifest["artifact_count"] = len(manifest["artifacts"])
    write_json(PACKAGE_MANIFEST, manifest)
    manifest["artifacts"].append(
        {
            "role": "handoff_manifest",
            "source": rel(PACKAGE_MANIFEST),
            "package_path": rel(PACKAGE_MANIFEST),
            "exists": PACKAGE_MANIFEST.exists(),
            "bytes": PACKAGE_MANIFEST.stat().st_size,
        }
    )
    manifest["artifact_count"] = len(manifest["artifacts"])
    write_json(PACKAGE_MANIFEST, manifest)
    manifest["zip"] = zip_package()
    write_json(PACKAGE_MANIFEST, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-HQ-PROVIDER-HANDOFF")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_package(args.task_id)
    if args.quiet:
        print(rel(PACKAGE_MANIFEST))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
