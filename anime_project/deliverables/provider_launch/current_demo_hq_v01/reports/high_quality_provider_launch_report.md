# High Quality Provider Launch Package

Task: TASK-056
Decision: current_demo_hq_launch_ready_blocked_by_submit_gate
Current demo: producer_demo_v02
Selected shots: 5
Selected providers: 2
Estimated first-pass paid cost: $2.84

## Launch Rows

| Queue | Shot | Provider | Cost | Gate | Return Path |
| --- | --- | --- | ---: | --- | --- |
| POLISH-001 | onsen_01_sample / ON-008 | kling_i2v | $1.44 | BLOCKED | anime_project\pipeline\external_results\inbox\kling_i2v\onsen_01_sample\ON-008\ON-008_kling_i2v.mp4 |
| POLISH-002 | act2_01_sample / 08-003 | kling_i2v | $0.36 | BLOCKED | anime_project\pipeline\external_results\inbox\kling_i2v\act2_01_sample\08-003\08-003_kling_i2v.mp4 |
| POLISH-003 | act2_01_sample / 08-004 | kling_i2v | $0.36 | BLOCKED | anime_project\pipeline\external_results\inbox\kling_i2v\act2_01_sample\08-004\08-004_kling_i2v.mp4 |
| POLISH-004 | act2_01_sample / 11-004 | kling_i2v | $0.36 | BLOCKED | anime_project\pipeline\external_results\inbox\kling_i2v\act2_01_sample\11-004\11-004_kling_i2v.mp4 |
| POLISH-005 | act2_01_sample / 12-002 | pika | $0.32 | BLOCKED | anime_project\pipeline\external_results\inbox\pika\act2_01_sample\12-002\12-002_pika.mp4 |

## Approval Controls

- No external request has been submitted by this package.
- Configure endpoint and token env vars for one provider first.
- Set provider approval env to true only after producer approval.
- Set cost cap env at or above the selected provider estimate.
- After returns arrive, run external ingest/review/replacement before updating the current demo.