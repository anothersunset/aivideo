# Producer Demo Package v02

Task: TASK-054
Decision: packaged_for_reviewed_local_polish_producer_demo_v02

## Main Playback

- `video/kage_preview_with_local_polish.mp4` is the current local-polish master preview.
- Specs verified in this package: 1920x1080, 24fps, H.264 video with AAC temp audio, about 184 seconds.
- This is still an internal producer demo, not a final release master.

## What Changed Since v01

- Promoted local polish shots: 5.
- Director/risk v02 review: conditional_pass_for_local_polish_producer_demo_v02 (5/5 keyframes nonblank).
- The promoted version keeps the previous multi-segment edit structure and adds versioned manifests instead of overwriting v01.
- Included evidence: local polish render manifest, promotion manifest, v02 director/risk review, contact sheets, and segment manifests.

## Contents

| Role | Package File | Bytes |
| --- | --- | ---: |
| master_preview_video | anime_project\deliverables\producer_demo_v02\video\kage_preview_with_local_polish.mp4 | 21723869 |
| master_manifest | anime_project\deliverables\producer_demo_v02\manifests\manifest_with_local_polish.json | 482 |
| local_polish_render_manifest | anime_project\deliverables\producer_demo_v02\manifests\local_polish_render_manifest.json | 8219 |
| local_polish_render_report | anime_project\deliverables\producer_demo_v02\reports\local_polish_render_report.md | 1383 |
| local_polish_promotion_manifest | anime_project\deliverables\producer_demo_v02\manifests\local_polish_promotion_manifest.json | 7725 |
| local_polish_promotion_report | anime_project\deliverables\producer_demo_v02\reports\local_polish_promotion_report.md | 1640 |
| director_risk_review_v02_manifest | anime_project\deliverables\producer_demo_v02\manifests\director_risk_review_v02_manifest.json | 6633 |
| director_risk_review_v02_report | anime_project\deliverables\producer_demo_v02\reports\director_risk_review_v02.md | 2323 |
| director_risk_review_v02_contact_sheet | anime_project\deliverables\producer_demo_v02\review\keyframes\v02_master_review_contact_sheet.png | 185892 |
| local_polish_contact_sheet | anime_project\deliverables\producer_demo_v02\review\keyframes\local_polish_contact_sheet.png | 186464 |
| local_polish_master_contact_sheet | anime_project\deliverables\producer_demo_v02\review\keyframes\local_polish_master_contact_sheet.png | 107945 |
| provider_registry | anime_project\deliverables\producer_demo_v02\manifests\provider_registry.json | 8130 |
| external_submit_gate_manifest | anime_project\deliverables\producer_demo_v02\manifests\external_submit_gate_manifest.json | 5230 |
| external_video_runbook | anime_project\deliverables\producer_demo_v02\docs\EXTERNAL_VIDEO_PIPELINE_RUNBOOK.md | 3305 |
| segment_manifest:onsen_01_sample | anime_project\deliverables\producer_demo_v02\manifests\segments\onsen_01_sample_manifest_with_local_polish.json | 7905 |
| segment_manifest:act2_01_sample | anime_project\deliverables\producer_demo_v02\manifests\segments\act2_01_sample_manifest_with_local_polish.json | 14415 |

## Next Production Step

Run director/risk review against v02, then either approve this as the current product demo or send the promoted shots to configured external providers for a higher-quality pass.