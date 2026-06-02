# Producer Demo Package v01

Task: TASK-046
Decision: packaged_for_internal_producer_demo

## Main Playback

- `video/kage_preview_with_replacements.mp4` is the current reviewed master preview.
- Specs verified upstream: 1920x1080, 24fps, H.264 video with AAC temp audio, about 184 seconds.

## Review State

- Master acceptance: ready_for_director_producer_review (6 checks passed, 0 failed).
- Director/risk review: conditional_pass_for_internal_producer_demo (5/5 keyframes nonblank).
- Final release ready: false. This is an internal producer demo package, not a locked release master.

## Contents

| Role | Package File | Bytes |
| --- | --- | ---: |
| master_preview_video | anime_project\deliverables\producer_demo_v01\video\kage_preview_with_replacements.mp4 | 20335654 |
| master_acceptance_report | anime_project\deliverables\producer_demo_v01\reports\master_acceptance_report.md | 1163 |
| master_acceptance_manifest | anime_project\deliverables\producer_demo_v01\manifests\master_acceptance_manifest.json | 6752 |
| director_risk_review_report | anime_project\deliverables\producer_demo_v01\reports\director_risk_review.md | 2331 |
| director_risk_review_manifest | anime_project\deliverables\producer_demo_v01\manifests\director_risk_review_manifest.json | 6073 |
| external_result_review_report | anime_project\deliverables\producer_demo_v01\reports\external_result_review.md | 478 |
| approved_external_results_manifest | anime_project\deliverables\producer_demo_v01\manifests\approved_external_results.json | 5630 |
| replacement_candidate_manifest | anime_project\deliverables\producer_demo_v01\manifests\replacement_candidate_manifest.json | 2349 |
| external_video_runbook | anime_project\deliverables\producer_demo_v01\docs\EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md | 3305 |
| provider_registry | anime_project\deliverables\producer_demo_v01\manifests\provider_registry.json | 8130 |
| external_submit_gate_manifest | anime_project\deliverables\producer_demo_v01\manifests\external_submit_gate_manifest.json | 5230 |
| contact_sheet | anime_project\deliverables\producer_demo_v01\review\keyframes\master_review_contact_sheet.png | 144647 |
| keyframe:ON-008 | anime_project\deliverables\producer_demo_v01\review\keyframes\onsen_01_sample_ON-008.png | 140265 |
| keyframe:08-003 | anime_project\deliverables\producer_demo_v01\review\keyframes\act2_01_sample_08-003.png | 264647 |
| keyframe:08-004 | anime_project\deliverables\producer_demo_v01\review\keyframes\act2_01_sample_08-004.png | 258140 |
| keyframe:11-004 | anime_project\deliverables\producer_demo_v01\review\keyframes\act2_01_sample_11-004.png | 304186 |
| keyframe:12-002 | anime_project\deliverables\producer_demo_v01\review\keyframes\act2_01_sample_12-002.png | 243677 |

## Next Production Step

Use this package for producer/director review, then choose one of two routes: approve as internal demo, or send the marked shots to high-quality external/video-model providers after credentials, budget caps, and producer approval are configured.