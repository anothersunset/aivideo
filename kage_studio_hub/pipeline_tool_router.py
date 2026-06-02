from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
PIPELINE_DIR = ANIME_PROJECT / "pipeline"
PROVIDER_REGISTRY_PATH = PIPELINE_DIR / "provider_registry.json"
JOB_ROOT = PIPELINE_DIR / "tool_jobs"

SEGMENT_ORDER = ["onsen_01_sample", "act2_01_sample"]


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def provider_registry() -> dict:
    return {
        "version": "0.1",
        "delivery_standard": {
            "resolution": "1920x1080",
            "fps": 24,
            "video_codec": "h264",
            "audio_codec": "aac",
            "mastering": "segment manifests -> master preview manifest",
        },
        "providers": {
            "local_2d_fallback": {
                "role": ["visual_design", "shot_animation", "audio", "edit"],
                "status": "active",
                "adapter": "sample_production_agent.py / onsen_segment_agent.py / master_edit_agent.py",
                "strength": "deterministic, no external account, full pipeline proof",
                "output": ["png", "wav", "mp4", "json"],
            },
            "remotion": {
                "role": ["code_video", "edit", "captions", "motion_graphics"],
                "status": "active_local_adapter",
                "adapter": "code_video_adapter_agent.py",
                "strength": "code-defined video packets, repeatable local renders, strong for packaging and compositing",
                "expected_inputs": ["composition_props.json", "assets", "audio"],
                "expected_outputs": ["shot.mp4", "segment.mp4"],
            },
            "hyperframes": {
                "role": ["html_to_video", "agentic_video_layout"],
                "status": "planned_adapter",
                "adapter": "adapters/hyperframes_adapter.ts",
                "strength": "agent-friendly HTML/CSS/JS video scene construction",
                "expected_inputs": ["html_scene.html", "assets", "render_manifest.json"],
                "expected_outputs": ["shot.mp4"],
            },
            "openai_image": {
                "role": ["keyframe", "character_sheet", "background_plate", "asset_variation"],
                "status": "planned_api_adapter",
                "adapter": "adapters/openai_image_adapter.py",
                "strength": "keyframe and design image generation before I2V",
                "expected_inputs": ["image_prompt", "reference_images", "safety_notes"],
                "expected_outputs": ["keyframe.png", "asset.png"],
            },
            "gemini": {
                "role": ["multimodal_review", "continuity_check", "image_prompting"],
                "status": "planned_api_adapter",
                "adapter": "adapters/gemini_review_adapter.py",
                "strength": "review frames, compare manifests, check continuity and risk",
                "expected_inputs": ["frames", "shot_manifest", "risk_rules"],
                "expected_outputs": ["review.json", "review.md"],
            },
            "kling_i2v": {
                "role": ["image_to_video", "shot_motion_refinement"],
                "status": "api_adapter_ready_config_required",
                "adapter": "external_video_provider_agent.py",
                "strength": "turn approved keyframes into high-quality motion clips",
                "expected_inputs": ["keyframe.png", "motion_prompt", "duration"],
                "expected_outputs": ["shot_video.mp4"],
            },
            "seedance_i2v": {
                "role": ["image_to_video", "shot_motion_refinement"],
                "status": "api_adapter_ready_config_required",
                "adapter": "external_video_provider_agent.py",
                "strength": "alternate I2V provider for style/motion A-B tests",
                "expected_inputs": ["keyframe.png", "motion_prompt", "duration"],
                "expected_outputs": ["shot_video.mp4"],
            },
            "runway": {
                "role": ["image_to_video", "text_to_video", "shot_motion_refinement"],
                "status": "api_adapter_ready_config_required",
                "adapter": "external_video_provider_agent.py",
                "strength": "commercial video generation option for high-quality shot variants",
                "expected_inputs": ["keyframe.png", "motion_prompt", "duration", "camera_notes"],
                "expected_outputs": ["shot_video.mp4"],
            },
            "luma": {
                "role": ["image_to_video", "text_to_video", "camera_motion"],
                "status": "api_adapter_ready_config_required",
                "adapter": "external_video_provider_agent.py",
                "strength": "cinematic motion exploration and alternate shot variants",
                "expected_inputs": ["keyframe.png", "motion_prompt", "duration"],
                "expected_outputs": ["shot_video.mp4"],
            },
            "pika": {
                "role": ["image_to_video", "stylized_motion", "short_shot_variants"],
                "status": "api_adapter_ready_config_required",
                "adapter": "external_video_provider_agent.py",
                "strength": "fast creative iteration for short motion tests",
                "expected_inputs": ["keyframe.png", "motion_prompt", "duration"],
                "expected_outputs": ["shot_video.mp4"],
            },
            "comfyui_svd": {
                "role": ["local_image_to_video", "open_source_workflow", "batch_generation"],
                "status": "planned_local_adapter",
                "adapter": "adapters/comfyui_svd_adapter.py",
                "strength": "local controllable workflows, lower vendor lock-in, batch queues",
                "expected_inputs": ["workflow.json", "keyframe.png", "motion_prompt"],
                "expected_outputs": ["shot_video.mp4", "workflow_outputs"],
            },
            "animatediff": {
                "role": ["local_image_to_video", "motion_lora_tests", "anime_motion"],
                "status": "planned_local_adapter",
                "adapter": "adapters/animatediff_adapter.py",
                "strength": "open-source anime-style motion experiments when local GPU is available",
                "expected_inputs": ["keyframe.png", "motion_prompt", "workflow_settings"],
                "expected_outputs": ["shot_video.mp4"],
            },
            "blender": {
                "role": ["3d_layout", "camera_previs", "background_projection"],
                "status": "planned_local_adapter",
                "adapter": "adapters/blender_previs_adapter.py",
                "strength": "repeatable camera layout, props, blocking, and previsualization",
                "expected_inputs": ["scene_layout.json", "camera_path.json", "assets"],
                "expected_outputs": ["previs.mp4", "layout_frames"],
            },
            "unreal": {
                "role": ["realtime_previs", "virtual_camera", "lighting_reference"],
                "status": "planned_manual_or_local_adapter",
                "adapter": "adapters/unreal_previs_adapter.py",
                "strength": "real-time staging and lighting reference if production needs 3D layout",
                "expected_inputs": ["scene_layout.json", "camera_path.json"],
                "expected_outputs": ["previs.mp4"],
            },
        },
        "routing_policy": {
            "default": "Use local_2d_fallback for proof and scheduled output. Use external providers only when credentials and approval are available.",
            "visual_design": ["openai_image", "gemini", "local_2d_fallback"],
            "shot_animation": [
                "kling_i2v",
                "seedance_i2v",
                "runway",
                "luma",
                "pika",
                "comfyui_svd",
                "animatediff",
                "remotion",
                "hyperframes",
                "local_2d_fallback",
            ],
            "previs": ["blender", "unreal", "remotion", "local_2d_fallback"],
            "edit": ["remotion", "local_2d_fallback"],
            "review": ["gemini", "local_2d_fallback"],
            "duration_chunking": "For external I2V adapters, split shots longer than 5 seconds into chunks unless the provider supports the full duration.",
        },
    }


def write_registry() -> dict:
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    registry = provider_registry()
    PROVIDER_REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_segment(segment: str) -> dict:
    base = ANIME_PROJECT / "episode_segments" / segment
    manifest = load_json(base / "manifest.json")
    animation_manifest = load_json(base / "animation_manifest.json")
    visual_manifest = load_json(base / "visual_assets_manifest.json") if (base / "visual_assets_manifest.json").exists() else {}
    return {
        "segment": segment,
        "base": base,
        "manifest": manifest,
        "animation_manifest": animation_manifest,
        "visual_manifest": visual_manifest,
    }


def chunks_for_duration(duration: float, max_chunk: float = 5.0) -> list[dict]:
    chunks = []
    count = max(1, math.ceil(duration / max_chunk))
    for index in range(count):
        start = min(duration, index * max_chunk)
        end = min(duration, (index + 1) * max_chunk)
        chunks.append(
            {
                "index": index + 1,
                "start_seconds": round(start, 3),
                "duration_seconds": round(max(0.0, end - start), 3),
            }
        )
    return chunks


def prompt_for_shot(segment: str, shot: dict) -> str:
    shot_id = shot["shot_id"]
    if segment == "onsen_01_sample":
        return (
            f"Adult 2D ninja action anime shot {shot_id}: rainy mountain onsen, night, hard silhouettes, "
            "restrained violence, clear readable action, original character and enemy design, no direct imitation."
        )
    return (
        f"Adult 2D ninja action anime shot {shot_id}: grim late-Edo fantasy, rain or fog, restrained body-horror, "
        "clear blade action, original silhouettes and symbols, no direct imitation."
    )


def make_shot_job(segment_data: dict, shot: dict, index: int) -> dict:
    segment = segment_data["segment"]
    segment_manifest = segment_data["manifest"]
    duration = float(shot.get("duration_seconds", 2.0))
    shot_video = shot["video"]
    shot_id = shot["shot_id"]
    keyframe_hint = f"anime_project/episode_segments/{segment}/final/key_{shot_id}.png"
    return {
        "job_id": f"{segment}_{index + 1:02d}_{shot_id}",
        "segment": segment,
        "shot_id": shot_id,
        "duration_seconds": duration,
        "fps": segment_manifest.get("fps", 24),
        "resolution": f"{segment_manifest.get('width', 1920)}x{segment_manifest.get('height', 1080)}",
        "current_local_output": shot_video,
        "prompt": prompt_for_shot(segment, shot),
        "risk_rules": [
            "Maintain original project identity; do not copy protected compositions or character designs.",
            "Keep violence readable but restrained for international cut options.",
            "For child-harm-adjacent scenes, use props, reaction, and silence instead of pain-process depiction.",
        ],
        "provider_routes": {
            "keyframe": {
                "preferred": ["openai_image", "gemini"],
                "fallback": "local_2d_fallback",
                "output": keyframe_hint,
            },
            "i2v_motion": {
                "preferred": ["kling_i2v", "seedance_i2v", "runway", "luma", "pika", "comfyui_svd", "animatediff"],
                "fallback": "remotion_or_local_2d_fallback",
                "chunks": chunks_for_duration(duration),
                "output": f"anime_project/episode_segments/{segment}/external_i2v/{shot_id}.mp4",
            },
            "code_render": {
                "preferred": ["remotion", "hyperframes"],
                "fallback": "local_2d_fallback",
                "composition_props": {
                    "shotId": shot_id,
                    "durationSeconds": duration,
                    "sourceVideo": shot_video,
                    "prompt": prompt_for_shot(segment, shot),
                },
            },
            "previs": {
                "preferred": ["blender", "unreal"],
                "fallback": "remotion_or_local_2d_fallback",
                "layout_request": {
                    "shotId": shot_id,
                    "durationSeconds": duration,
                    "camera": "derive from storyboard camera field and local fallback",
                    "blocking": "ronin, medic/archer, enemy silhouette, weather/space FX",
                },
                "output": f"anime_project/episode_segments/{segment}/previs/{shot_id}.mp4",
            },
            "review": {
                "preferred": ["gemini"],
                "fallback": "director_risk_manifest_review",
                "review_inputs": [shot_video, keyframe_hint],
            },
        },
        "status": "local_fallback_completed_external_pending",
    }


def build_segment_jobs(segment: str) -> dict:
    registry = write_registry()
    segment_data = load_segment(segment)
    shots = segment_data["animation_manifest"]["shots"]
    jobs = [make_shot_job(segment_data, shot, index) for index, shot in enumerate(shots)]
    segment_dir = JOB_ROOT / segment
    segment_dir.mkdir(parents=True, exist_ok=True)
    shot_jobs_path = segment_dir / "shot_jobs.json"
    shot_jobs_path.write_text(json.dumps({"segment": segment, "jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    queue_path = segment_dir / "external_queue.jsonl"
    queue_path.write_text("\n".join(json.dumps(job, ensure_ascii=False) for job in jobs), encoding="utf-8")
    routing_manifest = {
        "segment": segment,
        "provider_registry": rel(PROVIDER_REGISTRY_PATH),
        "source_manifest": rel(segment_data["base"] / "manifest.json"),
        "shot_count": len(jobs),
        "duration_seconds": segment_data["manifest"].get("duration_seconds"),
        "local_video": segment_data["manifest"].get("video"),
        "shot_jobs": rel(shot_jobs_path),
        "external_queue": rel(queue_path),
        "registry_version": registry["version"],
        "next_steps": [
            "Connect provider credentials.",
            "Implement one adapter at a time using this job schema.",
            "Replace shot videos in the segment manifest after approved external renders.",
            "Run master_edit_agent.py to rebuild the master preview.",
        ],
    }
    routing_path = segment_dir / "routing_manifest.json"
    routing_path.write_text(json.dumps(routing_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return routing_manifest


def build_master_jobs() -> dict:
    registry = write_registry()
    segments = [build_segment_jobs(segment) for segment in SEGMENT_ORDER]
    master_dir = JOB_ROOT / "master_preview"
    master_dir.mkdir(parents=True, exist_ok=True)
    master_manifest_path = ANIME_PROJECT / "episode_segments" / "master_preview" / "manifest.json"
    master_manifest = load_json(master_manifest_path)
    routing_manifest = {
        "target": "master_preview",
        "provider_registry": rel(PROVIDER_REGISTRY_PATH),
        "source_manifest": rel(master_manifest_path),
        "segments": segments,
        "shot_count": master_manifest.get("shot_count"),
        "duration_seconds": master_manifest.get("duration_seconds"),
        "local_video": master_manifest.get("video"),
        "recommended_pipeline": [
            "Generate or improve keyframes with OpenAI image/Gemini.",
            "Render selected S-shots with the best available I2V provider: Kling, Seedance, Runway, Luma, Pika, ComfyUI/SVD, or AnimateDiff.",
            "Package and stabilize edits with Remotion, HyperFrames, Blender/Unreal previs, or local fallback.",
            "Run Gemini/OpenAI multimodal review before replacing local fallback outputs.",
        ],
        "status": "local_pipeline_complete_external_provider_jobs_ready",
    }
    path = master_dir / "tool_routing_manifest.json"
    path.write_text(json.dumps(routing_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return routing_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["onsen_01_sample", "act2_01_sample", "master_preview"], default="master_preview")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.target == "master_preview":
        manifest = build_master_jobs()
        output_path = JOB_ROOT / "master_preview" / "tool_routing_manifest.json"
    else:
        manifest = build_segment_jobs(args.target)
        output_path = JOB_ROOT / args.target / "routing_manifest.json"
    if args.quiet:
        print(rel(output_path))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
