# Notion AI Handoff

This file is the GitHub-first entrypoint for Notion AI.

The project is not just text. It includes actual MP4, WAV, PNG, JSON, ZIP, manifests, a local Hub app, and a provider/MCP integration path.

## Current Repository State

- Repository: `https://github.com/anothersunset/aivideo.git`
- Branch: `main`
- Current safety state: no real paid/external provider call has been made.
- Current production state: playable 2D limited-animation prototype, provider-return simulation, and MCP local bridge rehearsal are all present in GitHub.
- Hub task count: 62 tasks in `kage_studio_hub/data/agent_tasks.json`.

## First Files To Read

1. `README.md`
2. `AIVIDEO_PROJECT_OVERVIEW.md`
3. `UPLOAD_MANIFEST.md`
4. `anime_project/EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md`
5. `anime_project/MCP_VIDEO_GATEWAY_PLAN.md`
6. `kage_studio_hub/data/agent_tasks.json`

## Playable MP4 Evidence

Open or inspect these files from GitHub/LFS:

- `anime_project/deliverables/current_demo/video/kage_current_demo.mp4`
- `anime_project/deliverables/producer_demo_v02/video/kage_preview_with_local_polish.mp4`
- `anime_project/deliverables/hq_provider_return_sim_v01/video/kage_preview_with_hq_sim_replacements.mp4`
- `anime_project/episode_segments/act2_01_sample/final/act2_01_sample_limited_animation.mp4`
- `anime_project/episode_segments/onsen_01_sample/final/onsen_01_sample_limited_animation.mp4`
- `anime_project/media/act2_storyboard_v02/act2_storyboard_v02_animatic.mp4`

## MCP Video Gateway Evidence

The MCP path is implemented far enough to prove local execution:

- Agent: `kage_studio_hub/mcp_video_gateway_agent.py`
- Local bridge simulation: `kage_studio_hub/mcp_video_bridge_sim.py`
- Provider profiles: `anime_project/pipeline/external_provider_profiles.json`
- Main gateway manifest: `anime_project/pipeline/mcp_video_gateway/mcp_video_gateway_manifest.json`
- Rehearsal report: `anime_project/pipeline/mcp_video_gateway/rehearsals/kling_i2v_local_sim/mcp_video_gateway_rehearsal_report.md`
- Rehearsal summary: `anime_project/pipeline/mcp_video_gateway/rehearsals/kling_i2v_local_sim/mcp_video_gateway_rehearsal_summary.json`

MCP local bridge rehearsal MP4 chunks:

- `anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/act2_01_sample/08-004/08-004_kling_i2v_chunk01.mp4`
- `anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/onsen_01_sample/ON-008/ON-008_kling_i2v_chunk01.mp4`
- `anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/onsen_01_sample/ON-008/ON-008_kling_i2v_chunk02.mp4`

These MP4 chunks are real local renders and explicitly marked as no external API call.

## Important Task Records

- `TASK-055`: current demo promotion.
- `TASK-056`: high-quality provider launch package.
- `TASK-057`: HQ provider handoff zip.
- `TASK-058`: simulated HQ provider returns.
- `TASK-059`: external result ingest.
- `TASK-060`: external result review.
- `TASK-061`: replacement/master rebuild.
- `TASK-062`: MCP video gateway dispatch and local bridge rehearsal.

## Do Not Assume

- Do not assume any commercial provider has been called.
- Do not assume current MP4s are final broadcast-quality animation.
- Do not submit paid jobs unless endpoint, token, cost cap, and producer/director approval are explicitly configured.
- Do not commit real secrets, private `.env` files, cookies, provider endpoints, or API tokens.

## Recommended Next Work

1. Choose one real provider route: Kling, Seedance, Pika, Runway, Luma, Gemini/Veo where available, ComfyUI, AnimateDiff, Remotion, or Hyperframes-like renderer.
2. Implement or install an MCP bridge for that route.
3. Keep the bridge contract compatible with `submit_video_job`.
4. Configure the submit gate with endpoint/tool credentials, approval, and cost cap.
5. Rerun `MCPVideoGatewayAgent` in execution mode.
6. Place returned MP4s in `anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/`.
7. Run ingest, review, replacement, and master rebuild.

## Local Verification Commands

```powershell
python -m py_compile kage_studio_hub\server.py kage_studio_hub\*.py
node --check kage_studio_hub\app.js
python scripts\verify_notion_handoff.py
python kage_studio_hub\server.py
```

Then inspect:

```text
http://127.0.0.1:8765/api/status
http://127.0.0.1:8765/api/pipeline
http://127.0.0.1:8765/api/tasks
```

GitHub Actions entrypoint:

- `.github/workflows/verify-handoff.yml`
