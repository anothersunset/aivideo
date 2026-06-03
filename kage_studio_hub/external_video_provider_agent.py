from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

try:
    from .provider_profile import PROFILES_PATH, write_default_profiles
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_profile import PROFILES_PATH, write_default_profiles

try:
    from .provider_env import readiness_for_env, token_env_candidates
except ImportError:  # pragma: no cover - supports direct script execution.
    from provider_env import readiness_for_env, token_env_candidates


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
PROVIDER_RUNS_DIR = PIPELINE_DIR / "provider_runs"
ADAPTER_RUNS_DIR = PIPELINE_DIR / "adapter_runs"
EXTERNAL_RESULTS_DIR = PIPELINE_DIR / "external_results"
INBOX_DIR = EXTERNAL_RESULTS_DIR / "inbox"

VIDEO_PROVIDERS = ["kling_i2v", "seedance_i2v", "runway", "luma", "pika"]
DEFAULT_TARGETS = {
    ("onsen_01_sample", "ON-008"),
    ("act2_01_sample", "08-004"),
}

PROVIDER_CONFIG = {
    "kling_i2v": {
        "display_name": "Kling image-to-video",
        "endpoint_env": "KAGE_KLING_I2V_ENDPOINT",
        "token_env": "KAGE_KLING_I2V_TOKEN",
        "submit_mode": "api_http_json_or_manual_portal",
    },
    "seedance_i2v": {
        "display_name": "Seedance image-to-video",
        "endpoint_env": "KAGE_SEEDANCE_I2V_ENDPOINT",
        "token_env": "KAGE_SEEDANCE_I2V_TOKEN",
        "submit_mode": "api_http_json_or_manual_portal",
    },
    "runway": {
        "display_name": "Runway video generation",
        "endpoint_env": "KAGE_RUNWAY_ENDPOINT",
        "token_env": "KAGE_RUNWAY_TOKEN",
        "submit_mode": "api_http_json_or_manual_portal",
    },
    "luma": {
        "display_name": "Luma video generation",
        "endpoint_env": "KAGE_LUMA_ENDPOINT",
        "token_env": "KAGE_LUMA_TOKEN",
        "submit_mode": "api_http_json_or_manual_portal",
    },
    "pika": {
        "display_name": "Pika video generation",
        "endpoint_env": "KAGE_PIKA_ENDPOINT",
        "token_env": "KAGE_PIKA_TOKEN",
        "submit_mode": "api_http_json_or_manual_portal",
    },
}


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def readiness_for(provider: str) -> dict:
    config = PROVIDER_CONFIG[provider]
    return readiness_for_env(provider, config["display_name"], config["submit_mode"])


def selected_packet_paths(provider: str, selected_only: bool) -> list[Path]:
    paths = sorted(PROVIDER_RUNS_DIR.glob(f"{provider}/*/*_i2v_requests.json"))
    if not selected_only:
        return paths
    selected = []
    for path in paths:
        packets = load_json(path)
        first = packets[0] if isinstance(packets, list) and packets else {}
        segment = path.parent.name
        shot_id = first.get("shot_id", "")
        if (segment, shot_id) in DEFAULT_TARGETS:
            selected.append(path)
    return selected


def build_submission_item(provider: str, packet_path: Path, chunk: dict) -> dict:
    segment = packet_path.parent.name
    shot_id = chunk["shot_id"]
    chunk_index = chunk.get("chunk_index", 1)
    return {
        "provider": provider,
        "job_id": chunk["job_id"],
        "segment": segment,
        "shot_id": shot_id,
        "chunk_index": chunk_index,
        "duration_seconds": chunk["duration_seconds"],
        "source_keyframe": chunk.get("source_keyframe", ""),
        "motion_prompt": chunk.get("motion_prompt", ""),
        "negative_prompt": chunk.get("negative_prompt", ""),
        "source_packet": rel(packet_path),
        "provider_expected_output": chunk.get("expected_output", ""),
        "expected_chunk_path": rel(
            EXTERNAL_RESULTS_DIR
            / "chunks"
            / provider
            / segment
            / shot_id
            / f"{shot_id}_{provider}_chunk{chunk_index:02d}.mp4"
        ),
        "expected_final_inbox_path": rel(INBOX_DIR / provider / segment / shot_id / f"{shot_id}_{provider}.mp4"),
        "chunk_assembly": "Drop chunk renders to expected_chunk_path; assemble the approved full shot to expected_final_inbox_path.",
        "status": "ready_for_submit",
    }


def write_config_example() -> str:
    write_default_profiles(PROFILES_PATH)
    example = {
        "purpose": "Fill these values through environment variables before enabling external submit.",
        "safety_policy": {
            "submit_requires": ["provider endpoint", "provider token", "human approval", "cost cap"],
            "download_target": "anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/",
            "post_download_gate": "ExternalResultIngestAgent validates 1920x1080, 24fps, duration, non-empty MP4.",
        },
        "provider_profiles": rel(PROFILES_PATH),
        "providers": PROVIDER_CONFIG,
        "token_aliases": {
            provider: token_env_candidates(provider)
            for provider in VIDEO_PROVIDERS
        },
    }
    path = PIPELINE_DIR / "external_provider_config.example.json"
    write_json(path, example)
    return rel(path)


def build_queue(provider: str, selected_only: bool) -> dict:
    ready = readiness_for(provider)
    packet_paths = selected_packet_paths(provider, selected_only)
    submissions = []
    for path in packet_paths:
        chunks = load_json(path)
        if not isinstance(chunks, list):
            continue
        submissions.extend(build_submission_item(provider, path, chunk) for chunk in chunks)

    run_dir = ADAPTER_RUNS_DIR / "external_video" / provider
    queue_path = run_dir / "submission_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in submissions), encoding="utf-8")

    manual_packet_path = run_dir / "manual_submission_packet.json"
    write_json(
        manual_packet_path,
        {
            "provider": provider,
            "instructions": [
                "Use these payloads in the provider portal/API only after human approval.",
                "Export/download each chunk to expected_chunk_path.",
                "If a shot has multiple chunks, assemble the final full shot before placing it at expected_final_inbox_path.",
                "Single-chunk shots can be copied directly to expected_final_inbox_path.",
                "Run ExternalResultIngestAgent after returns are placed in the inbox.",
            ],
            "submissions": submissions,
        },
    )

    status = "ready_for_api_submit" if ready["ready_for_api_submit"] else "waiting_for_provider_credentials"
    manifest = {
        "stage": "external_video_provider_submit",
        "mode": "prepare_submission_queue",
        "provider": provider,
        "selected_only": selected_only,
        "status": status,
        "created_at": int(time.time()),
        "readiness": ready,
        "packet_count": len(packet_paths),
        "submission_count": len(submissions),
        "queue": rel(queue_path),
        "manual_submission_packet": rel(manual_packet_path),
        "config_example": write_config_example(),
        "next_step": (
            "Set endpoint/token env vars and run with submit enabled, or manually submit the packet and drop MP4 returns into the inbox."
            if not ready["ready_for_api_submit"]
            else "Provider config is present; next implementation step is enabling submit/poll/download for this provider profile."
        ),
    }
    manifest_path = run_dir / "run_manifest.json"
    write_json(manifest_path, manifest)
    return manifest


def build_all(selected_only: bool) -> dict:
    manifests = [build_queue(provider, selected_only) for provider in VIDEO_PROVIDERS]
    ready_count = sum(1 for item in manifests if item["readiness"]["ready_for_api_submit"])
    summary = {
        "stage": "external_video_provider_submit_summary",
        "mode": "prepare_submission_queues",
        "providers": VIDEO_PROVIDERS,
        "selected_only": selected_only,
        "provider_count": len(manifests),
        "ready_provider_count": ready_count,
        "blocked_provider_count": len(manifests) - ready_count,
        "total_packet_count": sum(item["packet_count"] for item in manifests),
        "total_submission_count": sum(item["submission_count"] for item in manifests),
        "manifests": [rel(ADAPTER_RUNS_DIR / "external_video" / item["provider"] / "run_manifest.json") for item in manifests],
        "next_step": "Choose one provider, configure credentials/cost cap, then implement provider-specific submit/poll/download.",
    }
    summary_path = ADAPTER_RUNS_DIR / "external_video" / "summary_manifest.json"
    write_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["all", *VIDEO_PROVIDERS], default="all")
    parser.add_argument("--selected-only", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.provider == "all":
        manifest = build_all(args.selected_only)
        output_path = ADAPTER_RUNS_DIR / "external_video" / "summary_manifest.json"
    else:
        manifest = build_queue(args.provider, args.selected_only)
        output_path = ADAPTER_RUNS_DIR / "external_video" / args.provider / "run_manifest.json"

    if args.quiet:
        print(rel(output_path))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
