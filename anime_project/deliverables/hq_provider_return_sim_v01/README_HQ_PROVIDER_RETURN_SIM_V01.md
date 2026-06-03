# HQ Provider Return Simulation v01

## Purpose

This package is a handoff bundle for the current-demo high-quality provider return rehearsal. It proves the local pipeline can accept provider-style MP4 returns, validate them, review them, promote them as replacement candidates, and rebuild the master preview.

No external provider API call was made. All returned clips in this package are marked as `simulated_provider_return_no_external_api_call`.

## Contents

- `video/kage_preview_with_hq_sim_replacements.mp4`: master preview rebuilt after the simulated HQ return chain.
- `provider_returns/`: five simulated provider-return MP4 files generated into the expected external inbox format.
- `review_frames/hq_provider_return_sim_contact_sheet.png`: visual contact sheet for the simulated returns.
- `manifests/hq_provider_return_sim_manifest.json`: Hub-facing return simulation manifest.
- `manifests/simulated_hq_provider_returns.json`: chain-facing return simulation manifest.
- `manifests/validated_external_results.json`: ExternalResultIngestAgent scan result.
- `manifests/approved_external_results.json`: ExternalResultReviewAgent approval result.
- `manifests/master_manifest_with_hq_sim_replacements.json`: rebuilt master preview manifest, kept at `needs_director_review`.
- `reports/`: generated review and replacement reports.
- `code/`: the scripts used for the simulated return chain.

## Acceptance Snapshot

- Simulated provider returns: 5 generated, 5 accepted.
- Providers represented: 4 `kling_i2v`, 1 `pika`.
- Ingest: 7 accepted, 0 rejected, 0 unknown. The count includes two historical Remotion baseline returns plus the five simulated HQ returns.
- Review: 7 approved, 0 returned.
- Master preview status: `needs_director_review`.
- Master preview spec: H.264, 1920x1080, 24fps, about 184 seconds.

## Next Step

Use this package as a reviewable rehearsal artifact only. A director/producer should compare the simulated HQ replacement master against the current demo before any promotion. Real provider outputs should replace these simulated returns through the same inbox, ingest, review, and replacement flow.

