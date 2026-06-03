# AI Video Anime Production

This repository is the handoff source of truth for the Kage Studio AI-anime production prototype.

It contains a real, playable 2D limited-animation demo pipeline: scripts, Hub UI, manifests, rendered MP4/WAV/PNG assets, provider handoff packets, simulated provider returns, and MCP video-gateway rehearsal evidence.

## Start Here

For Notion AI or another downstream agent:

1. Read `NOTION_AI_HANDOFF.md`.
2. Read `AIVIDEO_PROJECT_OVERVIEW.md`.
3. Inspect `kage_studio_hub/data/agent_tasks.json`.
4. Verify playable videos under `anime_project/deliverables/` and `anime_project/episode_segments/`.
5. Continue from the MCP/provider integration path in `anime_project/MCP_VIDEO_GATEWAY_PLAN.md`.

## Current Playable Evidence

- Current producer demo MP4: `anime_project/deliverables/current_demo/video/kage_current_demo.mp4`
- Reviewed local-polish master: `anime_project/episode_segments/master_preview/final/kage_preview_with_local_polish.mp4`
- HQ provider simulation package: `anime_project/deliverables/hq_provider_return_sim_v01.zip`
- HQ simulated replacement master: `anime_project/deliverables/hq_provider_return_sim_v01/video/kage_preview_with_hq_sim_replacements.mp4`
- MCP local bridge rehearsal MP4 chunks:
  - `anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/act2_01_sample/08-004/08-004_kling_i2v_chunk01.mp4`
  - `anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/onsen_01_sample/ON-008/ON-008_kling_i2v_chunk01.mp4`
  - `anime_project/pipeline/mcp_video_gateway/local_sim_outputs/kling_i2v_rehearsal/anime_project/pipeline/external_results/chunks/kling_i2v/onsen_01_sample/ON-008/ON-008_kling_i2v_chunk02.mp4`

Media files are stored with Git LFS.

## What Is Implemented

- `VisualDesignAgent`, `AnimationAgent`, `AudioAgent`, and `EditAgent` create actual PNG/WAV/MP4/JSON outputs.
- Multi-segment preview assembly is implemented.
- External provider queues, submit gates, polling manifests, ingest, review, replacement, and master rebuild are implemented.
- HQ provider return simulation runs through ingest, review, and replacement without external API calls.
- `MCPVideoGatewayAgent` prepares MCP `submit_video_job` payloads for mainstream video-model bridges.
- `mcp_video_bridge_sim.py` proves the MCP bridge path can produce real H.264 MP4 chunks locally while keeping paid-provider gates blocked.

## Safety State

No paid or external provider call has been made.

The current default state is safe:

- `ExternalSubmitGateAgent` blocks all commercial providers unless endpoint, token, approval, and cost cap are configured.
- `MCPVideoGatewayAgent` defaults to prepare-only mode.
- MCP execution requires `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC=true` and a bridge command such as `KAGE_KLING_I2V_MCP_COMMAND`.
- Real secrets and private `.env` files are intentionally excluded.

## Local Hub

Run the project Hub locally:

```powershell
python kage_studio_hub\server.py
```

Then open:

```text
http://127.0.0.1:8765/
```

Useful API endpoints:

- `http://127.0.0.1:8765/api/status`
- `http://127.0.0.1:8765/api/pipeline`
- `http://127.0.0.1:8765/api/tasks`

## Key Documents

- `NOTION_AI_HANDOFF.md`
- `AIVIDEO_PROJECT_OVERVIEW.md`
- `UPLOAD_MANIFEST.md`
- `anime_project/EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md`
- `anime_project/MCP_VIDEO_GATEWAY_PLAN.md`
- `anime_project/pipeline/external_provider_profiles.json`
- `anime_project/pipeline/mcp_video_gateway/rehearsals/kling_i2v_local_sim/mcp_video_gateway_rehearsal_report.md`

## Next Production Step

Replace the local MCP bridge simulation with a real provider bridge for one approved provider, such as Kling, Seedance, Pika, Runway, Luma, Gemini/Veo where available, or a local ComfyUI/AnimateDiff workflow.

Keep the same contract:

`shot request -> MCP/HTTP/provider adapter -> MP4 inbox -> ingest -> review -> replacement -> master preview`
