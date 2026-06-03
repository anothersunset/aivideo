# Tests

Fast, dependency-light regression tests for the HQ provider-return chain.

## Run

```bash
python -m pip install pytest
python -m pytest
```

## Scope

- `test_pipeline_common.py` — encode contract constants (1920×1080/24), the
  provider whitelist/priority (Kling top), Windows-aware path normalization,
  and `run_checked` error surfacing (`MissingToolError` for absent binaries,
  `CommandError` carrying the exit code for non-zero exits).
- `test_verify_handoff.py` — path normalization plus the `backtick_paths`
  document-reference filter used by the handoff verifier (URLs, `KAGE_*`
  flags, and `TASK-*` ids excluded; project paths and top-level `.md` docs
  kept; paths with glob characters rejected).

These tests make **no external API calls** and only spawn the local Python
interpreter for the subprocess-error cases. The full media + manifest
verification still runs via `python scripts/verify_notion_handoff.py`.
