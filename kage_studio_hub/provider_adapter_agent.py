from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
TOOL_JOBS_DIR = PIPELINE_DIR / "tool_jobs"
RUNS_DIR = PIPELINE_DIR / "provider_runs"
SEGMENTS = ["onsen_01_sample", "act2_01_sample"]


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_queue(segment: str) -> list[dict]:
    path = TOOL_JOBS_DIR / segment / "external_queue.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def render_hyperframes_html(job: dict) -> str:
    title = f"{job['segment']} / {job['shot_id']}"
    prompt = job["prompt"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ margin:0; width:1920px; height:1080px; background:#101418; color:#f0ead4; font-family:Arial, sans-serif; }}
    .frame {{ position:absolute; inset:64px; border:4px solid #d6cfb5; overflow:hidden; }}
    .rain {{ position:absolute; inset:0; background:repeating-linear-gradient(105deg, transparent 0 70px, rgba(170,190,205,.25) 72px 75px, transparent 78px 140px); }}
    .title {{ position:absolute; left:72px; top:42px; font-size:34px; }}
    .prompt {{ position:absolute; left:92px; right:92px; bottom:72px; font-size:30px; line-height:1.35; background:rgba(0,0,0,.55); padding:24px; }}
    .shape {{ position:absolute; left:680px; top:340px; width:520px; height:300px; border:8px solid #dfe8ce; border-radius:50%; transform:skew(-12deg); }}
  </style>
</head>
<body>
  <div class="title">{title}</div>
  <div class="frame"><div class="rain"></div><div class="shape"></div></div>
  <div class="prompt">{prompt}</div>
</body>
</html>
"""


def openai_image_payload(job: dict) -> dict:
    return {
        "provider": "openai_image",
        "job_id": job["job_id"],
        "model": "gpt-image-1",
        "size": job["resolution"],
        "prompt": (
            job["prompt"]
            + "\nCreate one production keyframe for an original adult 2D ninja action anime. "
            + "Use strong silhouettes, restrained violence, no copied protected composition."
        ),
        "reference": {
            "local_fallback_video": job["current_local_output"],
            "risk_rules": job["risk_rules"],
        },
        "expected_output": job["provider_routes"]["keyframe"]["output"],
        "mode": "dry_run_request_packet",
    }


def gemini_review_payload(job: dict) -> dict:
    return {
        "provider": "gemini",
        "job_id": job["job_id"],
        "task": "multimodal_review",
        "inputs": job["provider_routes"]["review"]["review_inputs"],
        "questions": [
            "Does this shot preserve continuity with the segment manifest?",
            "Does it violate rating-risk rules?",
            "Does it appear too close to an existing protected anime composition?",
            "What should be fixed before replacing the local fallback shot?",
        ],
        "risk_rules": job["risk_rules"],
        "mode": "dry_run_request_packet",
    }


def i2v_payloads(job: dict, provider: str) -> list[dict]:
    payloads = []
    for chunk in job["provider_routes"]["i2v_motion"]["chunks"]:
        payloads.append(
            {
                "provider": provider,
                "job_id": job["job_id"],
                "shot_id": job["shot_id"],
                "chunk_index": chunk["index"],
                "duration_seconds": chunk["duration_seconds"],
                "source_keyframe": job["provider_routes"]["keyframe"]["output"],
                "motion_prompt": (
                    job["prompt"]
                    + f"\nAnimate this chunk from {chunk['start_seconds']}s for {chunk['duration_seconds']}s. "
                    + "Keep character identity, shot scale, and restrained adult-action tone consistent."
                ),
                "negative_prompt": "no modern objects, no comedy, no copied iconic compositions, no excessive gore",
                "expected_output": job["provider_routes"]["i2v_motion"]["output"].replace(".mp4", f"_{provider}_chunk{chunk['index']:02d}.mp4"),
                "mode": "dry_run_request_packet",
            }
        )
    return payloads


def local_workflow_payload(job: dict, provider: str) -> dict:
    return {
        "provider": provider,
        "job_id": job["job_id"],
        "shot_id": job["shot_id"],
        "workflow": "anime_i2v_motion_refinement",
        "source_keyframe": job["provider_routes"]["keyframe"]["output"],
        "motion_prompt": job["prompt"],
        "duration_seconds": job["duration_seconds"],
        "settings": {
            "fps": job["fps"],
            "resolution": job["resolution"],
            "identity_lock": True,
            "risk_rules": job["risk_rules"],
        },
        "expected_output": job["provider_routes"]["i2v_motion"]["output"].replace(".mp4", f"_{provider}.mp4"),
        "mode": "dry_run_request_packet",
    }


def previs_payload(job: dict, provider: str) -> dict:
    return {
        "provider": provider,
        "job_id": job["job_id"],
        "shot_id": job["shot_id"],
        "task": "3d_or_realtime_previs",
        "layout_request": job["provider_routes"]["previs"]["layout_request"],
        "duration_seconds": job["duration_seconds"],
        "fps": job["fps"],
        "resolution": job["resolution"],
        "expected_output": job["provider_routes"]["previs"]["output"].replace(".mp4", f"_{provider}.mp4"),
        "mode": "dry_run_request_packet",
    }


def remotion_props(job: dict) -> dict:
    return {
        "provider": "remotion",
        "composition": "ShotPackage",
        "job_id": job["job_id"],
        "props": job["provider_routes"]["code_render"]["composition_props"],
        "fps": job["fps"],
        "resolution": job["resolution"],
        "expected_output": f"anime_project/episode_segments/{job['segment']}/remotion/{job['shot_id']}.mp4",
        "mode": "dry_run_request_packet",
    }


def hyperframes_payload(job: dict, html_path: str) -> dict:
    return {
        "provider": "hyperframes",
        "job_id": job["job_id"],
        "html_scene": html_path,
        "duration_seconds": job["duration_seconds"],
        "fps": job["fps"],
        "resolution": job["resolution"],
        "expected_output": f"anime_project/episode_segments/{job['segment']}/hyperframes/{job['shot_id']}.mp4",
        "mode": "dry_run_request_packet",
    }


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_provider_packets(provider: str, segments: list[str]) -> dict:
    registry_path = PIPELINE_DIR / "provider_registry.json"
    registry = load_json(registry_path)
    run_dir = RUNS_DIR / provider
    run_dir.mkdir(parents=True, exist_ok=True)
    packet_paths = []
    jobs_processed = 0
    request_count = 0

    for segment in segments:
        for job in load_queue(segment):
            jobs_processed += 1
            base_name = safe_name(job["job_id"])
            if provider == "openai_image":
                path = run_dir / segment / f"{base_name}_keyframe_request.json"
                write_json(path, openai_image_payload(job))
                packet_paths.append(rel(path))
                request_count += 1
            elif provider == "gemini":
                path = run_dir / segment / f"{base_name}_review_request.json"
                write_json(path, gemini_review_payload(job))
                packet_paths.append(rel(path))
                request_count += 1
            elif provider in {"kling_i2v", "seedance_i2v", "runway", "luma", "pika"}:
                payloads = i2v_payloads(job, provider)
                path = run_dir / segment / f"{base_name}_i2v_requests.json"
                write_json(path, payloads)
                packet_paths.append(rel(path))
                request_count += len(payloads)
            elif provider in {"comfyui_svd", "animatediff"}:
                path = run_dir / segment / f"{base_name}_local_workflow_request.json"
                write_json(path, local_workflow_payload(job, provider))
                packet_paths.append(rel(path))
                request_count += 1
            elif provider in {"blender", "unreal"}:
                path = run_dir / segment / f"{base_name}_previs_request.json"
                write_json(path, previs_payload(job, provider))
                packet_paths.append(rel(path))
                request_count += 1
            elif provider == "remotion":
                path = run_dir / segment / f"{base_name}_remotion_props.json"
                write_json(path, remotion_props(job))
                packet_paths.append(rel(path))
                request_count += 1
            elif provider == "hyperframes":
                html_path = run_dir / segment / f"{base_name}_scene.html"
                html_path.parent.mkdir(parents=True, exist_ok=True)
                html_path.write_text(render_hyperframes_html(job), encoding="utf-8")
                payload_path = run_dir / segment / f"{base_name}_hyperframes_request.json"
                write_json(payload_path, hyperframes_payload(job, rel(html_path)))
                packet_paths.extend([rel(html_path), rel(payload_path)])
                request_count += 1
            else:
                raise ValueError(f"Unsupported provider: {provider}")

    manifest = {
        "provider": provider,
        "provider_status": registry["providers"][provider]["status"],
        "mode": "dry_run_no_external_api_call",
        "segments": segments,
        "jobs_processed": jobs_processed,
        "request_count": request_count,
        "registry": rel(registry_path),
        "packets": packet_paths,
        "submission_policy": "These packets are ready for adapter implementation. Do not submit externally until credentials, cost limits, and rights/risk review are configured.",
    }
    manifest_path = run_dir / "run_manifest.json"
    write_json(manifest_path, manifest)
    return manifest


def build_all() -> dict:
    providers = [
        "openai_image",
        "gemini",
        "kling_i2v",
        "seedance_i2v",
        "runway",
        "luma",
        "pika",
        "comfyui_svd",
        "animatediff",
        "remotion",
        "hyperframes",
        "blender",
        "unreal",
    ]
    manifests = [build_provider_packets(provider, SEGMENTS) for provider in providers]
    summary = {
        "mode": "dry_run_no_external_api_call",
        "providers": providers,
        "segments": SEGMENTS,
        "provider_run_manifests": [rel(RUNS_DIR / provider / "run_manifest.json") for provider in providers],
        "total_jobs_processed": sum(item["jobs_processed"] for item in manifests),
        "total_request_packets": sum(item["request_count"] for item in manifests),
        "next_step": "Implement one provider adapter submit/poll/download loop, then replace approved local fallback shots in segment manifests.",
    }
    summary_path = RUNS_DIR / "provider_run_summary.json"
    write_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        default="all",
        choices=[
            "all",
            "openai_image",
            "gemini",
            "kling_i2v",
            "seedance_i2v",
            "runway",
            "luma",
            "pika",
            "comfyui_svd",
            "animatediff",
            "remotion",
            "hyperframes",
            "blender",
            "unreal",
        ],
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.provider == "all":
        manifest = build_all()
        output_path = RUNS_DIR / "provider_run_summary.json"
    else:
        manifest = build_provider_packets(args.provider, SEGMENTS)
        output_path = RUNS_DIR / args.provider / "run_manifest.json"
    if args.quiet:
        print(rel(output_path))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
