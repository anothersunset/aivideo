from __future__ import annotations

import os


def provider_env_prefix(provider: str) -> str:
    return f"KAGE_{provider.upper()}"


def endpoint_env(provider: str) -> str:
    return f"{provider_env_prefix(provider)}_ENDPOINT"


def poll_endpoint_env(provider: str) -> str:
    return f"{provider_env_prefix(provider)}_POLL_ENDPOINT"


def token_env_candidates(provider: str) -> list[str]:
    prefix = provider_env_prefix(provider)
    return [f"{prefix}_TOKEN", f"{prefix}_API_KEY"]


def configured_env_name(candidates: list[str]) -> str:
    for name in candidates:
        if os.environ.get(name):
            return name
    return ""


def configured_env_value(candidates: list[str]) -> str:
    name = configured_env_name(candidates)
    return os.environ.get(name, "") if name else ""


def token_env(provider: str) -> str:
    candidates = token_env_candidates(provider)
    return configured_env_name(candidates) or candidates[0]


def token_value(provider: str) -> str:
    return configured_env_value(token_env_candidates(provider))


def endpoint_value(provider: str) -> str:
    return os.environ.get(endpoint_env(provider), "")


def readiness_for_env(provider: str, display_name: str = "", submit_mode: str = "") -> dict:
    endpoint = endpoint_value(provider)
    token = token_value(provider)
    candidates = token_env_candidates(provider)
    return {
        "provider": provider,
        "display_name": display_name,
        "submit_mode": submit_mode,
        "endpoint_env": endpoint_env(provider),
        "token_env": token_env(provider),
        "token_env_candidates": candidates,
        "token_env_used": configured_env_name(candidates),
        "has_endpoint": bool(endpoint),
        "has_token": bool(token),
        "ready_for_api_submit": bool(endpoint and token),
    }
