# MCP Video Bridge Contract

This contract lets another agent or provider-specific MCP server replace the local simulation bridge without changing the downstream Kage Studio pipeline.

## Tool

`submit_video_job`

Input schema:

- `anime_project/pipeline/mcp_video_gateway/schemas/submit_video_job.schema.json`

Output schema:

- `anime_project/pipeline/mcp_video_gateway/schemas/video_job_result.schema.json`

## Invocation

`MCPVideoGatewayAgent` sends one JSON payload to the configured bridge command through stdin.

The bridge command must print one JSON result to stdout.

Example environment:

```powershell
$env:KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC="true"
$env:KAGE_KLING_I2V_MCP_COMMAND="python kage_studio_hub\mcp_video_bridge_sim.py"
python kage_studio_hub\mcp_video_gateway_agent.py --task-id TASK-MCP-BRIDGE
```

Generic HTTP bridge template:

```powershell
$env:KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC="true"
$env:KAGE_KLING_I2V_MCP_COMMAND="python kage_studio_hub\mcp_http_video_bridge.py"
$env:KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC="true"
$env:KAGE_KLING_I2V_ENDPOINT="https://provider-or-mcp-adapter.example/submit"
$env:KAGE_KLING_I2V_TOKEN="<configured outside git>"
python kage_studio_hub\mcp_video_gateway_agent.py --task-id TASK-MCP-BRIDGE
```

Provider-specific command envs override the global command:

- `KAGE_KLING_I2V_MCP_COMMAND`
- `KAGE_SEEDANCE_I2V_MCP_COMMAND`
- `KAGE_PIKA_MCP_COMMAND`
- `KAGE_RUNWAY_MCP_COMMAND`
- `KAGE_LUMA_MCP_COMMAND`
- Global fallback: `KAGE_MCP_VIDEO_GATEWAY_COMMAND`

## Required Bridge Behavior

1. Accept a single `submit_video_job` JSON object on stdin.
2. Submit to a real model, local renderer, browser automation, or local simulation.
3. Return a JSON object with at least `status`, `job_id`, `provider`, `segment`, `shot_id`, and `chunk_index`.
4. When the job is complete, write or download an H.264 MP4 to either:
   - `expected_chunk_path` for chunk assembly, or
   - `expected_final_inbox_path` for direct ingest.
5. Never print secrets or full provider tokens to stdout/stderr.
6. Leave final acceptance to `ExternalResultIngestAgent`, `ExternalResultReviewAgent`, and `ShotReplacementAgent`.

## Output Contract

Completed bridge outputs should satisfy:

- H.264 video.
- `1920x1080`.
- `24fps`.
- Duration close to `duration_seconds`.
- Non-empty MP4.
- Traceable `job_id`.
- `external_api_call` set to `true` only if a real external provider was called.
- `simulated` set to `true` only for local rehearsals.

## Safety Gate

Do not run a real provider bridge until all of these are true:

- `ExternalSubmitGateAgent` allows the provider.
- Provider credentials or tool auth are configured outside Git.
- Producer/director approval is explicit.
- Provider or global cost cap is configured.
- The bridge implementation is reviewed for secret handling.

`mcp_http_video_bridge.py` is safe by default. It returns a queued result and makes no HTTP request unless `KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC=true`.

The current repository default remains prepare-only and blocked for paid providers.
