"""Shared constants and helpers for the HQ provider-return simulation chain.

Single source of truth for the TASK-058..061 chain so that target shots,
provider routing, segment list, path handling and subprocess error reporting
stay consistent across every agent.

Guardrails: NO external API call, NO HTTP submit/poll, NO API key, NO secret.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path, PureWindowsPath


# Fallback target shots used only when no reviewed external results exist.
# TASK-058 itself uses provider_launch/current_demo_hq_v01 launch_rows as the
# source of truth so it stays aligned with the current operator handoff package.
TARGET_SHOTS: list[dict] = [
    {"segment": "onsen_01_sample", "shot_id": "ON-008", "provider": "kling_i2v"},
    {"segment": "act2_01_sample", "shot_id": "08-004", "provider": "kling_i2v"},
]

# Segments that participate in the simulated provider-return chain.
SEGMENTS: list[str] = ["onsen_01_sample", "act2_01_sample"]

# Provider routing priority (higher = preferred). The keys also define the
# accepted-provider whitelist used by the ingest agent.
PROVIDER_PRIORITY: dict[str, int] = {
    "kling_i2v": 100,
    "seedance_i2v": 95,
    "runway": 90,
    "luma": 85,
    "pika": 80,
    "comfyui_svd": 60,
    "animatediff": 55,
    "hyperframes": 50,
    "remotion": 30,
    "blender": 25,
    "unreal": 25,
}

# Whitelisted providers (derived from PROVIDER_PRIORITY to avoid duplication).
VIDEO_PROVIDERS: list[str] = list(PROVIDER_PRIORITY.keys())

# Encode contract enforced across the whole chain.
WIDTH, HEIGHT, FPS = 1920, 1080, 24


class MissingToolError(RuntimeError):
    """Raised when ffmpeg/ffprobe is not installed.

    This is an ENVIRONMENT error and must be surfaced as a hard failure, not
    silently recorded as a rejected / low-quality result.
    """


class CommandError(RuntimeError):
    """Raised when an ffmpeg/ffprobe command exits non-zero.

    Carries the decoded stderr so failures are debuggable instead of opaque.
    """


def normalize_path(raw: str) -> Path:
    """Normalize a manifest path that may use Windows backslashes.

    ``shot_jobs.json`` / ``agent_tasks.json`` store paths like
    ``anime_project\\episode_segments\\...``. On POSIX, ``Path`` would treat the
    backslashes as part of a single filename, so opening the file fails.
    ``PureWindowsPath`` understands both separators; ``as_posix`` yields a clean
    forward-slash path usable on any OS.
    """
    if raw is None:
        raise ValueError("path is None")
    return Path(PureWindowsPath(str(raw)).as_posix())


def resolve_workspace_path(workspace: Path, raw: str) -> Path:
    """Resolve a (possibly Windows-style, possibly relative) path against the
    workspace root."""
    p = normalize_path(raw)
    return p if p.is_absolute() else workspace / p


def ensure_tool(tool: str) -> None:
    if shutil.which(tool) is None:
        raise MissingToolError(
            f"required tool '{tool}' not found on PATH; install FFmpeg before running the chain"
        )


def run_checked(
    cmd: list[str],
    *,
    cwd: str | None = None,
    capture_text: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess and raise informative errors.

    - Raises :class:`MissingToolError` when the binary is absent (environment).
    - Raises :class:`CommandError` with decoded stderr on a non-zero exit.
    """
    tool = cmd[0]
    ensure_tool(tool)
    try:
        return subprocess.run(
            cmd,
            check=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=capture_text,
            encoding="utf-8" if capture_text else None,
        )
    except FileNotFoundError as exc:  # pragma: no cover - guarded by ensure_tool
        raise MissingToolError(f"{tool} not found: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        raise CommandError(
            f"{tool} failed (exit {exc.returncode}): {' '.join(cmd)}\n"
            f"{stderr or '<no stderr captured>'}"
        ) from exc
