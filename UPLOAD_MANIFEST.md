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

The HQ provider simulation/review/replacement rehearsal has been executed and packaged as `anime_project/deliverables/hq_provider_return_sim_v01.zip`. No paid or external provider call has been made, and the rebuilt replacement master remains `needs_director_review`.

This upload is intended to let Notion AI or another downstream agent accept the work from the current state without needing hidden local context.
