# Current Demo HQ Provider Handoff v01

Task: TASK-057
Decision: current_demo_hq_provider_handoff_packaged

## Purpose

This package prepares the current internal demo for a first high-quality provider pass. It does not submit any external request.

## Launch Summary

- Current demo version: producer_demo_v02
- Selected shots: 5
- Selected providers: 2
- Estimated first-pass cost: $2.84
- Submit status: not_submitted_blocked_by_submit_gate

## Required Before Submit

- Fill provider endpoint and token environment variables.
- Set provider cost cap at or above the estimate.
- Set provider submit approval to true only after producer/director approval.
- Rerun ExternalSubmitGateAgent before ExternalProviderSubmitAgent.

## Contents

| Role | Package File | Bytes |
| --- | --- | ---: |
| launch_manifest | anime_project\deliverables\provider_launch\current_demo_hq_v01\manifests\high_quality_provider_launch_manifest.json | 15827 |
| launch_report | anime_project\deliverables\provider_launch\current_demo_hq_v01\reports\high_quality_provider_launch_report.md | 1581 |
| provider_config_template | anime_project\deliverables\provider_launch\current_demo_hq_v01\config\external_provider_config.current_demo_hq.template.json | 968 |
| env_example | anime_project\deliverables\provider_launch\current_demo_hq_v01\config\.env.current_demo_hq.example | 430 |
| selected_launch_rows | anime_project\deliverables\provider_launch\current_demo_hq_v01\manifests\selected_provider_launch_rows.jsonl | 11052 |
| current_demo_manifest | anime_project\deliverables\provider_launch\current_demo_hq_v01\current_demo\current_demo_manifest.json | 3167 |
| current_demo_readme | anime_project\deliverables\provider_launch\current_demo_hq_v01\current_demo\CURRENT_PRODUCER_DEMO.md | 787 |
| provider_packet:kling_i2v | anime_project\deliverables\provider_launch\current_demo_hq_v01\providers\kling_i2v_launch_packet.json | 11110 |
| provider_packet:pika | anime_project\deliverables\provider_launch\current_demo_hq_v01\providers\pika_launch_packet.json | 2918 |
| keyframe:POLISH-001 | anime_project\deliverables\provider_launch\current_demo_hq_v01\keyframes\POLISH-001_onsen_01_sample_ON-008.png | 73652 |
| keyframe:POLISH-002 | anime_project\deliverables\provider_launch\current_demo_hq_v01\keyframes\POLISH-002_act2_01_sample_08-003.png | 276552 |
| keyframe:POLISH-003 | anime_project\deliverables\provider_launch\current_demo_hq_v01\keyframes\POLISH-003_act2_01_sample_08-004.png | 184849 |
| keyframe:POLISH-004 | anime_project\deliverables\provider_launch\current_demo_hq_v01\keyframes\POLISH-004_act2_01_sample_11-004.png | 569386 |
| keyframe:POLISH-005 | anime_project\deliverables\provider_launch\current_demo_hq_v01\keyframes\POLISH-005_act2_01_sample_12-002.png | 524544 |

## Next Step

Configure provider credentials and cost cap, rerun ExternalSubmitGateAgent, then submit only the approved provider rows.