# AI Video Anime Production Project

This repository contains the current Kage Studio anime production prototype: a local agent hub, production manifests, rendered 2D limited-animation sample videos, review packages, and provider handoff materials.

It is packaged as a handoff bundle for another AI workspace or Notion AI: the repository includes both the executable local pipeline and the production evidence needed to understand what has already been built.

## Current Result

- Current demo package: `anime_project/deliverables/current_demo/current_producer_demo.zip`
- Current demo MP4: `anime_project/deliverables/current_demo/video/kage_current_demo.mp4`
- Reviewed local-polish master: `anime_project/episode_segments/master_preview/final/kage_preview_with_local_polish.mp4`
- HQ provider handoff zip: `anime_project/deliverables/current_demo_hq_provider_handoff_v01.zip`
- HQ provider return simulation package: `anime_project/deliverables/hq_provider_return_sim_v01.zip`
- Hub entrypoint: `kage_studio_hub/server.py`
- Hub task record: `kage_studio_hub/data/agent_tasks.json`

The current demo is a playable 2D limited-animation prototype with actual MP4/WAV/PNG/JSON outputs. It is not final broadcast-quality animation, but it is designed to be reviewable, replaceable shot-by-shot, and ready for high-quality provider integration.

## Production Architecture

The workflow is organized around media-producing agents:

- `VisualDesignAgent`, `AnimationAgent`, `AudioAgent`, and `EditAgent` produce core boards, shot videos, temp audio, and assembled edits.
- External/provider agents prepare request packets, submit gates, provider polling, inbox validation, review, and replacement edits.
- Producer/director/risk agents package demos, extract evidence frames, and record approval status.
- High-quality provider launch and handoff agents prepare Kling/Pika-style provider rows, config templates, keyframes, and operator packages without submitting paid jobs.

The intended production model is multi-video assembly: each shot or segment can be generated independently, validated through manifests, then stitched into a master preview.

## Current Pause Point

The video generation/replacement pipeline was paused before executing the newly queued HQ provider return simulation tasks. The repo includes the code and task records created up to that pause point, but no real external provider submission has been made.

The previously pending TASK-058..061 simulation chain has now been run and packaged:

- `TASK-058` `HQProviderReturnSimAgent`
- `TASK-059` `ExternalResultIngestAgent`
- `TASK-060` `ExternalResultReviewAgent`
- `TASK-061` `ShotReplacementAgent`

These rehearse high-quality provider return ingest/review/replacement using simulated MP4 returns, explicitly marked as `simulated_provider_return_no_external_api_call`. The rebuilt replacement master remains `needs_director_review`.

## Notion AI Handoff Notes

Use this repository as the source of truth for the project state. Start with:

- `UPLOAD_MANIFEST.md` for upload scope and pause status.
- `anime_project/deliverables/current_demo/CURRENT_PRODUCER_DEMO.md` for current producer-facing demo notes.
- `anime_project/EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md` for provider ingest/review/replacement workflow.
- `kage_studio_hub/data/agent_tasks.json` for approved, queued, and paused tasks.
- `anime_project/deliverables/current_demo/current_demo_manifest.json` for current demo artifacts.
- `anime_project/deliverables/hq_provider_return_sim_v01/README_HQ_PROVIDER_RETURN_SIM_V01.md` for the simulated HQ return chain package.

## Future Provider Integration

The repo is structured so that real providers can replace local simulation stages later:

- Kling / Kuaishou-style image-to-video
- Seedance-style image-to-video
- Pika / Runway / Luma style short video generation
- Gemini/OpenAI image or video generation where supported by available APIs
- Local/open-source fallbacks such as Remotion, ComfyUI/SVD, AnimateDiff, or Hyperframes-like code-video pipelines

The invariant is that provider outputs must return as traceable MP4 files under `anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/`, then pass ingest, review, and replacement before becoming part of the demo.
