from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
PROFILES_PATH = PIPELINE_DIR / "external_provider_profiles.json"

DEFAULT_JOB_ID_PATHS = [
    "job_id",
    "id",
    "task_id",
    "generation_id",
    "data.job_id",
    "data.id",
    "data.task_id",
    "data.generation_id",
    "result.job_id",
    "result.id",
]

DEFAULT_STATUS_PATHS = [
    "status",
    "state",
    "data.status",
    "data.state",
    "result.status",
    "result.state",
    "task.status",
]

DEFAULT_MEDIA_URL_PATHS = [
    "video_url",
    "media_url",
    "output_url",
    "data.video_url",
    "data.media_url",
    "data.output_url",
    "data.result.video_url",
    "data.result.media_url",
    "result.video_url",
    "result.media_url",
    "output.video_url",
    "output.media_url",
    "outputs.0.video_url",
    "outputs.0.url",
]

SUCCESS_STATUSES = ["succeeded", "complete", "completed", "done", "success", "finished"]

BASE_PROFILE = {
    "schema_version": "kage_external_provider_profile_v1",
    "auth": "bearer_token_header",
    "submit": {
        "method": "POST",
        "payload_mode": "kage_standard_i2v_json",
        "response_job_id_paths": DEFAULT_JOB_ID_PATHS,
    },
    "poll": {
        "method": "GET",
        "query_param": "id",
        "response_status_paths": DEFAULT_STATUS_PATHS,
        "response_media_url_paths": DEFAULT_MEDIA_URL_PATHS,
        "success_statuses": SUCCESS_STATUSES,
    },
    "download": {
        "mode": "operator_or_adapter_download_to_inbox",
        "target": "anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/",
    },
}

DEFAULT_PROVIDER_PROFILES = {
    "kling_i2v": {
        "display_name": "Kling image-to-video",
        "notes": "Configure with the current Kling/Kuaishou API or manual portal response shape.",
    },
    "seedance_i2v": {
        "display_name": "Seedance image-to-video",
        "notes": "Configure with the current Seedance/ByteDance API or manual portal response shape.",
    },
    "runway": {
        "display_name": "Runway video generation",
        "notes": "Configure with the current Runway task/generation response shape.",
    },
    "luma": {
        "display_name": "Luma video generation",
        "notes": "Configure with the current Luma generation response shape.",
    },
    "pika": {
        "display_name": "Pika video generation",
        "notes": "Configure with the current Pika task/generation response shape.",
    },
}


def default_profiles() -> dict:
    providers = {}
    for provider, metadata in DEFAULT_PROVIDER_PROFILES.items():
        profile = copy.deepcopy(BASE_PROFILE)
        profile.update(metadata)
        providers[provider] = profile
    return {
        "schema_version": "kage_external_provider_profiles_v1",
        "purpose": "Configurable response parsing for real video provider submit/poll adapters.",
        "secret_policy": "Do not store endpoints or tokens here; use environment variables only.",
        "providers": providers,
    }


def write_default_profiles(path: Path = PROFILES_PATH) -> dict:
    payload = default_profiles()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_profiles() -> dict:
    if PROFILES_PATH.exists():
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return default_profiles()


def provider_profile(provider: str) -> dict:
    profiles = load_profiles()
    base = copy.deepcopy(BASE_PROFILE)
    provider_config = profiles.get("providers", {}).get(provider, {})
    base.update(provider_config)
    base.setdefault("submit", {}).setdefault("response_job_id_paths", DEFAULT_JOB_ID_PATHS)
    base.setdefault("poll", {}).setdefault("response_status_paths", DEFAULT_STATUS_PATHS)
    base.setdefault("poll", {}).setdefault("response_media_url_paths", DEFAULT_MEDIA_URL_PATHS)
    base["poll"].setdefault("success_statuses", SUCCESS_STATUSES)
    return base


def extract_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return ""
            continue
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current[part]
    return current


def first_path_value(payload: Any, paths: list[str]) -> str:
    for path in paths:
        value = extract_path(payload, path)
        if value not in (None, "", [], {}):
            return str(value)
    return ""


def extract_provider_job_id(provider: str, response: dict) -> str:
    profile = provider_profile(provider)
    paths = profile.get("submit", {}).get("response_job_id_paths", DEFAULT_JOB_ID_PATHS)
    return first_path_value(response, paths)


def extract_remote_status(provider: str, response: dict) -> str:
    profile = provider_profile(provider)
    paths = profile.get("poll", {}).get("response_status_paths", DEFAULT_STATUS_PATHS)
    return first_path_value(response, paths)


def extract_media_url(provider: str, response: dict) -> str:
    profile = provider_profile(provider)
    paths = profile.get("poll", {}).get("response_media_url_paths", DEFAULT_MEDIA_URL_PATHS)
    return first_path_value(response, paths)


def success_statuses(provider: str) -> set[str]:
    profile = provider_profile(provider)
    return {str(item).lower() for item in profile.get("poll", {}).get("success_statuses", SUCCESS_STATUSES)}
