# Upload Manifest

## Repository Target

- Remote: `https://github.com/anothersunset/aivideo.git`
- Upload mode: direct HTTPS push
- Media storage: Git LFS

## Included

- `anime_project/`: production documents, storyboards, manifests, videos, audio, keyframes, deliverables, provider launch and handoff artifacts.
- `kage_studio_hub/`: local Hub server, frontend, agents, task records, pipeline status code.
- Root project notes: README, `main.py`, and deployment/background documents already present in the workspace.
- `AIVIDEO_PROJECT_OVERVIEW.md`: overall scheme, current outputs, pause point, provider integration route.

## Excluded

- Local virtual environments and dependency folders.
- IDE folders and machine-specific caches.
- Python bytecode, temporary files, logs, and real secret/env files.
- Unrelated local projects such as `Graphrag-copilot/`.
- Empty local folders such as `review/`.

## LFS Rules

Git LFS tracks media and delivery artifacts:

- `*.mp4`
- `*.wav`
- `*.zip`
- `*.png`
- `*.jpg`
- `*.jpeg`
- `*.webp`

## Current Pipeline Status

The active video-generation work is intentionally paused for upload. Newly queued HQ provider simulation/review/replacement tasks are present but should not be executed as part of this upload. No paid or external provider call has been made.

This upload is intended to let Notion AI or another downstream agent accept the work from the current state without needing hidden local context.
