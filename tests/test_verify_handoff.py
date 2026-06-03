"""Regression tests for scripts/verify_notion_handoff.py pure helpers.

Media (ffprobe) and manifest-on-disk checks are exercised by running the
script itself in CI/locally; here we lock the path-handling and document
reference-extraction logic that is easy to break during refactors.
"""
from __future__ import annotations

import verify_notion_handoff as vh


def test_normalize_handles_backslashes():
    assert vh.normalize("anime_project\\x\\y.mp4").as_posix() == "anime_project/x/y.mp4"


def test_project_path_resolves_under_root():
    assert vh.project_path("README.md") == vh.ROOT / "README.md"


def test_root_points_at_repository_root():
    assert (vh.ROOT / "scripts" / "verify_notion_handoff.py").exists()


def test_backtick_paths_accepts_project_paths_in_order():
    md = "see `anime_project/a.mp4` and `scripts/verify_notion_handoff.py`."
    assert vh.backtick_paths(md) == [
        "anime_project/a.mp4",
        "scripts/verify_notion_handoff.py",
    ]


def test_backtick_paths_accepts_top_level_markdown_docs():
    assert vh.backtick_paths("`README.md`") == ["README.md"]


def test_backtick_paths_skips_urls_env_flags_and_task_ids():
    md = "`https://example.com/x` `KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC` `TASK-062`"
    assert vh.backtick_paths(md) == []


def test_backtick_paths_skips_unknown_bare_tokens():
    assert vh.backtick_paths("`foo/bar` `plainword`") == []


def test_backtick_paths_skips_paths_with_glob_chars():
    assert vh.backtick_paths("`anime_project/with<bad>.mp4`") == []
