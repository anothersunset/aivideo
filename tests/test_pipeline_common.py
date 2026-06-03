"""Regression tests for kage_studio_hub/pipeline_common.py.

These lock the single-source-of-truth invariants of the HQ provider-return
simulation chain so future refactors cannot silently drift the encode
contract, provider whitelist, path handling, or subprocess error reporting.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

import pipeline_common as pc


def test_target_shots_match_contract():
    pairs = {(s["segment"], s["shot_id"], s["provider"]) for s in pc.TARGET_SHOTS}
    assert ("onsen_01_sample", "ON-008", "kling_i2v") in pairs
    assert ("act2_01_sample", "08-004", "kling_i2v") in pairs


def test_segments_are_the_two_chain_segments():
    assert pc.SEGMENTS == ["onsen_01_sample", "act2_01_sample"]


def test_video_providers_derived_from_priority():
    assert pc.VIDEO_PROVIDERS == list(pc.PROVIDER_PRIORITY.keys())


def test_kling_is_top_priority_provider():
    assert pc.PROVIDER_PRIORITY["kling_i2v"] == max(pc.PROVIDER_PRIORITY.values())


def test_encode_contract_constants():
    assert (pc.WIDTH, pc.HEIGHT, pc.FPS) == (1920, 1080, 24)


def test_normalize_path_handles_windows_backslashes():
    out = pc.normalize_path("anime_project\\episode_segments\\a.mp4")
    assert out.as_posix() == "anime_project/episode_segments/a.mp4"


def test_normalize_path_preserves_forward_slashes():
    assert pc.normalize_path("anime_project/x/y.mp4").as_posix() == "anime_project/x/y.mp4"


def test_normalize_path_rejects_none():
    with pytest.raises(ValueError):
        pc.normalize_path(None)


def test_resolve_workspace_path_joins_relative(tmp_path):
    out = pc.resolve_workspace_path(tmp_path, "anime_project\\x.mp4")
    assert out == tmp_path / "anime_project" / "x.mp4"


@pytest.mark.skipif(os.name == "nt", reason="POSIX absolute-path semantics")
def test_resolve_workspace_path_keeps_absolute():
    assert pc.resolve_workspace_path(Path("/ws"), "/abs/x.mp4") == Path("/abs/x.mp4")


def test_ensure_tool_missing_raises():
    with pytest.raises(pc.MissingToolError):
        pc.ensure_tool("kage_definitely_missing_tool_xyz")


def test_ensure_tool_present_does_not_raise(monkeypatch):
    monkeypatch.setattr(pc.shutil, "which", lambda _tool: "/usr/bin/ffmpeg")
    pc.ensure_tool("ffmpeg")


def test_run_checked_missing_tool_raises():
    with pytest.raises(pc.MissingToolError):
        pc.run_checked(["kage_definitely_missing_tool_xyz", "--version"])


def test_run_checked_success_captures_stdout():
    result = pc.run_checked([sys.executable, "-c", "print('ok')"], capture_text=True)
    assert result.returncode == 0
    assert "ok" in result.stdout


def test_run_checked_nonzero_raises_command_error_with_exit_code():
    with pytest.raises(pc.CommandError) as excinfo:
        pc.run_checked([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert "exit 3" in str(excinfo.value)
