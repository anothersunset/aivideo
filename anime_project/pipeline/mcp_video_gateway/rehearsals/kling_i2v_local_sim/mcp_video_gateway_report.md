# MCP Video Gateway Report

Task: TASK-062-MCP-LOCAL-SIM-REHEARSAL
Mode: execute_mcp_bridge
Dispatch items: 15
Submitted via MCP bridge: 3
Prepared only: 0
Blocked: 12

## Provider Summary

| Provider | Dispatches | Submitted | Prepared | Blocked | Provider Bridge Env | Global Bridge Env |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| kling_i2v | 3 | 3 | 0 | 0 | `KAGE_KLING_I2V_MCP_COMMAND` | `KAGE_MCP_VIDEO_GATEWAY_COMMAND` |
| luma | 3 | 0 | 0 | 3 | `KAGE_LUMA_MCP_COMMAND` | `KAGE_MCP_VIDEO_GATEWAY_COMMAND` |
| pika | 3 | 0 | 0 | 3 | `KAGE_PIKA_MCP_COMMAND` | `KAGE_MCP_VIDEO_GATEWAY_COMMAND` |
| runway | 3 | 0 | 0 | 3 | `KAGE_RUNWAY_MCP_COMMAND` | `KAGE_MCP_VIDEO_GATEWAY_COMMAND` |
| seedance_i2v | 3 | 0 | 0 | 3 | `KAGE_SEEDANCE_I2V_MCP_COMMAND` | `KAGE_MCP_VIDEO_GATEWAY_COMMAND` |

## Execution Controls

- No MCP bridge execution occurs unless `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC=true`.
- Configure a global bridge command with `KAGE_MCP_VIDEO_GATEWAY_COMMAND`, or provider-specific commands like `KAGE_KLING_I2V_MCP_COMMAND`.
- The bridge must accept one JSON payload on stdin and return JSON on stdout.
- Returned MP4s must still land in the expected external-results inbox and pass ingest/review/replacement.