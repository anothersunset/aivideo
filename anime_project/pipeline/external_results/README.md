# External Result Inbox

Drop externally generated MP4 files here using this path convention:

`inbox/{provider}/{segment}/{shot_id}/{shot_id}_{provider}.mp4`

Example:

`inbox/runway/onsen_01_sample/ON-008/ON-008_runway.mp4`

Validation rules:

- 1920x1080
- 24fps
- MP4 with video stream
- Duration close to the shot job duration
- File is non-empty

Accepted files are recorded in `manifests/validated_external_results.json`.
