from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
DELIVERABLES_DIR = ANIME_PROJECT / "deliverables"
CURRENT_DIR = DELIVERABLES_DIR / "current_demo"
V01_MANIFEST = DELIVERABLES_DIR / "producer_demo_v01" / "producer_demo_manifest.json"
V02_MANIFEST = DELIVERABLES_DIR / "producer_demo_v02" / "producer_demo_v02_manifest.json"
CURRENT_MANIFEST = CURRENT_DIR / "current_demo_manifest.json"
CURRENT_README = CURRENT_DIR / "CURRENT_PRODUCER_DEMO.md"
DEMO_REGISTRY = DELIVERABLES_DIR / "demo_version_registry.json"


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def file_record(path: Path, role: str) -> dict:
    return {
        "role": role,
        "path": rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }


def zip_entry_count(path: Path) -> int:
    with zipfile.ZipFile(path, "r") as archive:
        return len(archive.infolist())


def copy_current_artifacts(v02: dict) -> list[dict]:
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    (CURRENT_DIR / "video").mkdir(parents=True, exist_ok=True)

    v02_zip = WORKSPACE / v02.get("zip", {}).get("path", "")
    v02_video = WORKSPACE / v02.get("master_video", "")
    v02_manifest = V02_MANIFEST
    v02_readme = DELIVERABLES_DIR / "producer_demo_v02" / "README_PRODUCER_DEMO_V02.md"

    targets = [
        (v02_zip, CURRENT_DIR / "current_producer_demo.zip", "current_demo_zip"),
        (v02_video, CURRENT_DIR / "video" / "kage_current_demo.mp4", "current_demo_video"),
        (v02_manifest, CURRENT_DIR / "producer_demo_v02_manifest.json", "source_v02_manifest"),
        (v02_readme, CURRENT_DIR / "README_PRODUCER_DEMO_V02.md", "source_v02_readme"),
    ]
    artifacts = []
    for source, target, role in targets:
        if not source.exists():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        artifacts.append(file_record(target, role))
    return artifacts


def registry_entry(version: str, manifest_path: Path, manifest: dict, current: bool) -> dict:
    zip_path = WORKSPACE / manifest.get("zip", {}).get("path", "")
    return {
        "version": version,
        "current": current,
        "decision": manifest.get("decision", "not_run"),
        "manifest": rel(manifest_path) if manifest_path.exists() else "",
        "zip": rel(zip_path) if zip_path.exists() else "",
        "zip_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
        "artifact_count": manifest.get("artifact_count", 0),
        "master_video": manifest.get("master_video", ""),
    }


def build_readme(manifest: dict) -> str:
    return "\n".join(
        [
            "# Current Producer Demo",
            "",
            f"Task: {manifest['task_id']}",
            f"Current version: {manifest['current_version']}",
            f"Decision: {manifest['decision']}",
            "",
            "## Stable Playback",
            "",
            "- `video/kage_current_demo.mp4` is the current internal producer demo video.",
            "- `current_producer_demo.zip` is the current packaged handoff zip.",
            "- Source version remains traceable through `producer_demo_v02_manifest.json`.",
            "",
            "## Evidence",
            "",
            f"- Source package decision: {manifest['source_package']['decision']}",
            f"- Director/risk v02 review: {manifest['director_review_v02']['decision']} ({manifest['director_review_v02']['nonblank_keyframe_count']}/{manifest['director_review_v02']['reviewed_keyframe_count']} keyframes nonblank).",
            f"- Promoted local-polish shots: {manifest['local_polish_promotion']['promoted_count']}",
            "",
            "## Next Step",
            "",
            manifest["next_step"],
        ]
    )


def run_promotion(task_id: str) -> dict:
    v01 = load_json(V01_MANIFEST, {})
    v02 = load_json(V02_MANIFEST, {})
    if v02.get("decision") != "packaged_for_reviewed_local_polish_producer_demo_v02":
        raise ValueError("producer_demo_v02 is not reviewed and packaged")
    director_v02 = v02.get("director_review_v02", {})
    if director_v02.get("decision") != "conditional_pass_for_local_polish_producer_demo_v02":
        raise ValueError("producer_demo_v02 director/risk review is not passable")

    artifacts = copy_current_artifacts(v02)
    current_zip = CURRENT_DIR / "current_producer_demo.zip"
    current_video = CURRENT_DIR / "video" / "kage_current_demo.mp4"
    manifest = {
        "task_id": task_id,
        "stage": "current_demo_promotion",
        "decision": "producer_demo_v02_promoted_to_current_internal_demo",
        "current_version": "producer_demo_v02",
        "current_zip": rel(current_zip),
        "current_video": rel(current_video),
        "source_manifest": rel(V02_MANIFEST),
        "source_package": {
            "decision": v02.get("decision", "not_run"),
            "artifact_count": v02.get("artifact_count", 0),
            "zip": v02.get("zip", {}),
        },
        "director_review_v02": director_v02,
        "local_polish_promotion": v02.get("local_polish_promotion", {}),
        "artifacts": artifacts,
        "zip_entry_count": zip_entry_count(current_zip),
        "final_release_ready": False,
        "readme": rel(CURRENT_README),
        "registry": rel(DEMO_REGISTRY),
        "next_step": "Use current_demo as the stable producer handoff, then route selected shots to configured external providers for the next high-quality pass.",
    }
    CURRENT_README.write_text(build_readme(manifest), encoding="utf-8")
    manifest["artifacts"].append(file_record(CURRENT_README, "current_demo_readme"))
    write_json(CURRENT_MANIFEST, manifest)
    manifest["manifest"] = rel(CURRENT_MANIFEST)
    write_json(CURRENT_MANIFEST, manifest)

    registry = {
        "task_id": task_id,
        "stage": "demo_version_registry",
        "current_version": "producer_demo_v02",
        "current_manifest": rel(CURRENT_MANIFEST),
        "versions": [
            registry_entry("producer_demo_v01", V01_MANIFEST, v01, False),
            registry_entry("producer_demo_v02", V02_MANIFEST, v02, True),
        ],
        "next_step": manifest["next_step"],
    }
    write_json(DEMO_REGISTRY, registry)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="TASK-CURRENT-DEMO-PROMOTION")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = run_promotion(args.task_id)
    if args.quiet:
        print(manifest["manifest"])
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
