# External Video Pipeline Runbook

## Current State

- Local limited-animation master is live.
- Remotion-style local code-video return workflow is proven.
- Commercial I2V providers are queued but blocked until credentials, approval, and cost caps are configured.
- No commercial provider request is sent by default.

## Production Chain

1. `ToolRouterAgent`
   - Builds shot jobs and provider registry.
   - Output: `anime_project/pipeline/tool_jobs/`.

2. `ProviderAdapterAgent`
   - Converts shot jobs into provider-specific request packets.
   - Output: `anime_project/pipeline/provider_runs/`.

3. `ExternalVideoProviderAgent`
   - Builds selected commercial I2V submission queues for Kling, Seedance, Runway, Luma, and Pika.
   - Output: `anime_project/pipeline/adapter_runs/external_video/`.

4. `ExternalSubmitGateAgent`
   - Blocks all external submit unless each provider has endpoint, token, approval, and cost cap.
   - Output: `anime_project/pipeline/submit_gate/external_submit_gate_manifest.json`.

5. `ExternalProviderSubmitAgent`
   - Submits only providers that passed the gate.
   - Current mode: blocked, no external submit.
   - Output: `anime_project/pipeline/submit_runs/external_video/submit_run_manifest.json`.

6. `ExternalProviderPollAgent`
   - Polls submitted jobs when provider polling is configured.
   - Output: `anime_project/pipeline/poll_runs/external_video/poll_run_manifest.json`.

7. `ExternalChunkAssemblyAgent`
   - Assembles returned chunks into final shot MP4s.
   - Chunk path: `anime_project/pipeline/external_results/chunks/{provider}/{segment}/{shot_id}/`.
   - Final inbox path: `anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/`.

8. `ExternalResultIngestAgent`
   - Validates returned MP4s.
   - Gate: 1920x1080, 24fps, duration close to shot job, non-empty MP4.

9. `ShotReplacementAgent`
   - Promotes accepted external results into replacement candidates.
   - Rebuilds segment replacement manifests and master replacement preview.

## Current Commercial I2V Targets

- `onsen_01_sample / ON-008`
- `act2_01_sample / 08-004`

Each provider receives 3 chunks:

- `08-004`: one 2s chunk.
- `ON-008`: one 5s chunk and one 3s chunk.

## Required Env Before Real Submit

For one provider, configure:

- Endpoint env, for example `KAGE_KLING_I2V_ENDPOINT`.
- Token env, preferred example `KAGE_KLING_I2V_TOKEN`.
- Legacy token alias, still accepted: `KAGE_KLING_I2V_API_KEY`.
- Approval env, for example `KAGE_KLING_I2V_SUBMIT_APPROVED=true`.
- Cost cap env, for example `KAGE_KLING_I2V_COST_CAP_USD=5`.
- Optional global cap: `KAGE_EXTERNAL_VIDEO_COST_CAP_USD=10`.

HTTP submit remains disabled unless:

- `KAGE_EXTERNAL_VIDEO_ENABLE_HTTP_SUBMIT=true`

HTTP poll remains disabled unless:

- `KAGE_EXTERNAL_VIDEO_ENABLE_HTTP_POLL=true`

## Provider Profiles

- Provider response parsing is configured in `anime_project/pipeline/external_provider_profiles.json`.
- Profiles define where to find provider job ids, remote status values, and returned video URLs in submit/poll JSON responses.
- Do not store real endpoints or tokens in profiles. Keep credentials in env vars only.
- For a new or changed provider API, update the profile paths first, then rerun `ExternalVideoProviderAgent`, `ExternalSubmitGateAgent`, `ExternalProviderSubmitAgent`, and `ExternalProviderPollAgent`.
- MCP-based provider tools should follow `anime_project/MCP_VIDEO_GATEWAY_PLAN.md` and write outputs to the same inbox paths.

## Current Verified Outputs

- `anime_project/episode_segments/master_preview/final/kage_preview_with_replacements.mp4`
- `anime_project/pipeline/external_results/inbox/remotion/onsen_01_sample/ON-008/ON-008_remotion.mp4`
- `anime_project/pipeline/external_results/inbox/remotion/act2_01_sample/08-004/08-004_remotion.mp4`

## Review Rule

Do not approve commercial I2V submit until the director and producer agree on:

- Provider choice.
- Shot list.
- Cost cap.
- Rating-risk handling.
- Originality boundary language.
- Returned MP4 review responsibility.
