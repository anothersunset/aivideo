# MCP Video Gateway Plan

## Goal

Use MCP as a stable gateway between Kage Studio agents and external video/image tools. The Hub should keep one production contract:

1. Build shot request payloads.
2. Submit through a provider adapter.
3. Poll or receive returned jobs.
4. Download or place MP4s in the inbox.
5. Run ingest, review, and replacement.

The provider implementation can be HTTP API, MCP tool, local software, or manual UI handoff. The downstream pipeline should not care as long as traceable MP4/PNG/JSON outputs are written.

## Current State

- No real paid provider request has been made.
- Generic HTTP submit/poll agents exist and are blocked by endpoint, token, approval, and cost cap gates.
- Provider credential env names use `KAGE_{PROVIDER}_TOKEN` first and accept `KAGE_{PROVIDER}_API_KEY` as a legacy alias.
- `anime_project/pipeline/external_provider_profiles.json` defines provider response parsing for job ids, statuses, and media URLs.
- `MCPVideoGatewayAgent` prepares standard MCP `submit_video_job` payloads from the existing provider queues.
- Current simulated HQ returns prove the ingest/review/replacement chain without calling an external model.

## MCP Gateway Shape

An MCP video provider server should expose a small stable tool set:

- `list_video_models`
  - Returns provider model ids, max duration, supported input modes, cost hints, and output specs.
- `submit_video_job`
  - Inputs: provider, model, segment, shot_id, keyframe path, prompt, negative prompt, duration, fps, resolution, safety notes, expected inbox path.
  - Output: provider job id, provider response summary, estimated cost, status.
- `poll_video_job`
  - Inputs: provider, provider job id.
  - Output: status, progress, media URL or download handle.
- `download_video_result`
  - Inputs: provider, provider job id, media URL or handle, expected inbox path.
  - Output: local MP4 path, bytes, checksum.
- `submit_image_job`
  - Optional keyframe/design generation for OpenAI/Gemini/image providers before I2V.

## Supported Provider Routes

Use the same production contract for:

- Kling/Kuaishou-style image-to-video.
- Seedance-style image-to-video.
- Pika, Runway, and Luma short video generation.
- Gemini/Veo-style video tools where API/tooling is available.
- OpenAI image/keyframe tools before I2V.
- Local ComfyUI/SVD/AnimateDiff workflows.
- Remotion or Hyperframes-like code-video renderers.
- Browser/UI automation fallback for providers that do not expose a stable API.

## Adapter Priority

1. MCP provider server if available.
2. Direct HTTP API adapter using `external_provider_profiles.json`.
3. Local CLI/software adapter.
4. Browser or manual portal handoff with manifest-controlled inbox return.

## Safety And Cost Gate

Every route must keep the same gates:

- No real submit unless endpoint/tool credentials are configured.
- No real submit unless producer/director approval env is true.
- No real submit unless provider or global cost cap is configured and sufficient.
- Never commit real tokens, cookies, provider endpoints, or private `.env` files.
- Returned media must be validated before replacement.

## Repository Integration

The current implementation already prepares the contract:

- Requests: `anime_project/pipeline/adapter_runs/external_video/{provider}/submission_queue.jsonl`
- Profiles: `anime_project/pipeline/external_provider_profiles.json`
- MCP dispatch queue: `anime_project/pipeline/mcp_video_gateway/mcp_video_dispatch_queue.jsonl`
- MCP gateway manifest: `anime_project/pipeline/mcp_video_gateway/mcp_video_gateway_manifest.json`
- Submit gate: `anime_project/pipeline/submit_gate/external_submit_gate_manifest.json`
- Returned chunks: `anime_project/pipeline/external_results/chunks/{provider}/{segment}/{shot_id}/`
- Final returned shots: `anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/`
- Review and replacement: `ExternalResultIngestAgent`, `ExternalResultReviewAgent`, `ShotReplacementAgent`

## Next Implementation Step

Install or implement a real MCP provider bridge that accepts one JSON payload on stdin and returns JSON on stdout. Then set either `KAGE_MCP_VIDEO_GATEWAY_COMMAND` or a provider-specific command such as `KAGE_KLING_I2V_MCP_COMMAND`, configure submit-gate credentials/approval/cost caps, and rerun `MCPVideoGatewayAgent` with `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC=true`.

Until that MCP bridge exists, the generic HTTP and manual handoff paths remain the working fallback.
