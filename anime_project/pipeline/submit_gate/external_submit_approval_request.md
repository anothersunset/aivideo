# External Video Submit Approval Request

Task: TASK-038

No external request is submitted by this gate. A provider is allowed only when endpoint, token, approval, and cost cap are all present.

| Provider | Chunks | Seconds | Est. Cost | Cap | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| kling_i2v | 3 | 10.0 | $1.8 | $0.0 | BLOCKED: has_endpoint, has_token, submit_approved, cost_cap_configured, cost_within_cap |
| luma | 3 | 10.0 | $2.2 | $0.0 | BLOCKED: has_endpoint, has_token, submit_approved, cost_cap_configured, cost_within_cap |
| pika | 3 | 10.0 | $1.6 | $0.0 | BLOCKED: has_endpoint, has_token, submit_approved, cost_cap_configured, cost_within_cap |
| runway | 3 | 10.0 | $2.4 | $0.0 | BLOCKED: has_endpoint, has_token, submit_approved, cost_cap_configured, cost_within_cap |
| seedance_i2v | 3 | 10.0 | $1.8 | $0.0 | BLOCKED: has_endpoint, has_token, submit_approved, cost_cap_configured, cost_within_cap |

Approval controls:

- Set `KAGE_{PROVIDER}_SUBMIT_APPROVED=true` only after producer/director approval.
- Set `KAGE_{PROVIDER}_COST_CAP_USD` or `KAGE_EXTERNAL_VIDEO_COST_CAP_USD` before submit.
- Keep returned chunks under `anime_project/pipeline/external_results/chunks/...`.
- Run `ExternalChunkAssemblyAgent`, then `ExternalResultIngestAgent`, then replacement review.