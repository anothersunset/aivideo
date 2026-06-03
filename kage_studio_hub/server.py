from __future__ import annotations

import json
import mimetypes
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
DATA_DIR = ROOT / "data"
TASKS_FILE = DATA_DIR / "agent_tasks.json"
OUTPUT_DIR = DATA_DIR / "outputs"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def write_json(path: Path, payload) -> None:
    ensure_data_dir()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def project_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return WORKSPACE / path


def file_status(raw_path: str | None) -> dict:
    path = project_path(raw_path)
    exists = bool(path and path.exists())
    return {
        "path": raw_path or "",
        "exists": exists,
        "bytes": path.stat().st_size if exists and path and path.is_file() else 0,
        "mtime": path.stat().st_mtime if exists and path else None,
    }


def write_output_markdown(task_id: str, content: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{task_id}_writer_output.md"
    path.write_text(content, encoding="utf-8")
    return str(path.relative_to(ROOT))


def write_named_output_markdown(task_id: str, suffix: str, content: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{task_id}_{suffix}.md"
    path.write_text(content, encoding="utf-8")
    return str(path.relative_to(ROOT))


def categorize_document(name: str) -> str:
    if "Agent" in name:
        return "Tech"
    if "雨夜温泉宿" in name or "试制片" in name or "样片" in name:
        return "Sample"
    if "剧本" in name or "剧情" in name or "角色" in name:
        return "Script"
    if "投资" in name or "PPT" in name:
        return "Finance"
    if "预算" in name or "排期" in name or "开发" in name:
        return "Production"
    if "视觉" in name or "百骸" in name:
        return "Art"
    return "Overview"


def summarize_markdown(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="ignore")
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("#").strip()
        if line and not line.startswith("---") and len(line) > 4:
            return line[:120]
    return "Development package document"


def list_documents() -> list[dict]:
    docs = []
    for path in sorted(ANIME_PROJECT.glob("*.md")):
        docs.append(
            {
                "category": categorize_document(path.name),
                "name": path.name,
                "summary": summarize_markdown(path),
                "bytes": path.stat().st_size,
                "mtime": path.stat().st_mtime,
            }
        )
    return docs


SHOTS = [
    ["001", "Rainy onsen exterior", "A", "Storyboard", "Night rain, lamp light, atmosphere"],
    ["002", "Rinzo watches from roof", "B", "Storyboard", "First character impression"],
    ["003", "Tobi copies the secret letter", "B", "Storyboard", "Black fever, furnace, port, blood sample"],
    ["004", "Hallucination incense enters", "B", "Storyboard", "Transparent smoke and oil lamp"],
    ["005", "Hall panic", "A", "To storyboard", "Crowd violence under hallucination"],
    ["006", "Raindrop on blade", "C", "To storyboard", "Stillness before action"],
    ["007", "Rinzo crashes through roof", "S", "Key shot", "First visual impact"],
    ["008", "Triple kill", "S", "Key shot", "Speed and lethal intent"],
    ["009", "Tobi shoots out lamp", "A", "Storyboard", "Creates darkness"],
    ["010", "Mizumoni upside down", "A", "Design", "Enemy silhouette reveal"],
    ["011", "Tobi crushes medicine pills", "B", "To storyboard", "Medicine smoke vs hallucination incense"],
    ["012", "Blade slides off poison membrane", "S", "Key shot", "Poison membrane rule test"],
    ["013", "Poison needle splits hat", "A", "To storyboard", "Pressure beat"],
    ["014", "Ordinary blade wounds fail", "B", "To storyboard", "Character relationship beat"],
    ["015", "Silk binds sword", "S", "Key shot", "Close action and enemy rule"],
    ["016", "Old medicine whisper", "A", "To storyboard", "Main-plot hook"],
    ["017", "Tobi blocks needle with medicine box", "A", "To storyboard", "Mutual rescue and whiteout"],
    ["018", "Whiteout silhouette fight", "S", "Key shot", "Style showcase"],
    ["019", "Lantern in water reveals membrane", "S", "Key shot", "Main visual memory point"],
    ["020", "Corridor escape and letter backup", "A", "To storyboard", "Information and escape rhythm"],
    ["021", "Rain ending", "S", "Key shot", "Story hook and wrist scar"],
]


AGENTS = [
    ["DirectorAgent", "Reviews creative direction, action clarity, character fidelity.", "Planned"],
    ["ProducerAgent", "Tracks budget, schedule, scope changes, and reports.", "MVP"],
    ["WriterAgent", "Expands script, compresses dialogue, repairs arcs.", "MVP"],
    ["StoryboardAgent", "Turns script into shot suggestions and storyboard text.", "Planned"],
    ["VisualDesignAgent", "Generates character, enemy, and setting prompt directions.", "MVP"],
    ["AnimationAgent", "Renders shot-level 2D limited animation videos.", "MVP"],
    ["ActionAgent", "Breaks down combat rules, key poses, and readability.", "Planned"],
    ["CompAgent", "Designs rain, smoke, fire, blood, and membrane comp layers.", "Planned"],
    ["AudioAgent", "Generates temp sound, ambience, and rhythm tracks.", "MVP"],
    ["EditAgent", "Concatenates segment videos, audio, subtitles, and manifests.", "MVP"],
    ["ToolRouterAgent", "Builds provider registry and external generation job packets.", "MVP"],
    ["ProviderAdapterAgent", "Converts standard shot jobs into provider-specific dry-run request packets.", "MVP"],
    ["CodeVideoAdapterAgent", "Renders Remotion-style code-video packets into real MP4 files for the external inbox.", "MVP"],
    ["ExternalVideoProviderAgent", "Prepares configurable submit queues for Kling, Seedance, Runway, Luma, and Pika.", "MVP"],
    ["ExternalChunkAssemblyAgent", "Assembles returned provider chunks into final MP4 inbox files.", "MVP"],
    ["ExternalSubmitGateAgent", "Blocks external submits until credentials, producer approval, and cost caps are configured.", "MVP"],
    ["ExternalProviderSubmitAgent", "Submits only providers that pass the gate and records pending external jobs.", "MVP"],
    ["ExternalProviderPollAgent", "Polls/downloads submitted provider jobs when external polling is configured.", "MVP"],
    ["MCPVideoGatewayAgent", "Prepares or executes MCP video-model dispatch payloads for approved provider queues.", "MVP"],
    ["ExternalResultReviewAgent", "Reviews accepted external MP4s before replacement edit approval.", "MVP"],
    ["ShotReplacementAgent", "Tests external-shot replacement, review, manifest backfill, and re-edit workflow.", "MVP"],
    ["MasterAcceptanceAgent", "Aggregates master video, segment, replacement, review, and submit-gate acceptance evidence.", "MVP"],
    ["DirectorRiskReviewAgent", "Extracts review keyframes and prepares director/risk evidence for producer demo approval.", "MVP"],
    ["DirectorRiskReviewV2Agent", "Reviews local-polish producer demo v02 keyframes and risk rules.", "MVP"],
    ["ProducerDemoPackageAgent", "Packages reviewed MP4, reports, keyframes, manifests, and zip for producer demo delivery.", "MVP"],
    ["ProducerDemoV2PackageAgent", "Packages the local-polish master preview as a versioned producer demo v02 zip.", "MVP"],
    ["CurrentDemoPromotionAgent", "Promotes the reviewed demo package into stable current_demo handoff paths.", "MVP"],
    ["HighQualityPolishQueueAgent", "Builds provider-ready polish work orders and handoff packets for reviewed priority shots.", "MVP"],
    ["HighQualityProviderLaunchAgent", "Builds current-demo high-quality provider launch packets, env templates, and cost controls.", "MVP"],
    ["HighQualityProviderHandoffPackageAgent", "Packages HQ provider launch packets, keyframes, and config into an operator handoff zip.", "MVP"],
    ["HQProviderReturnSimAgent", "Simulates high-quality provider MP4 returns into the external inbox for ingest/review backfill rehearsal.", "MVP"],
    ["LocalPolishRenderAgent", "Renders local Remotion-style polish MP4 candidates for queued priority shots.", "MVP"],
    ["LocalPolishPromoteAgent", "Promotes accepted local polish clips into versioned segment and master preview manifests.", "MVP"],
    ["ProductionReviewClosureAgent", "Approves evidence-backed completed tasks and leaves unresolved creative/returned tasks open.", "MVP"],
    ["ExternalResultIngestAgent", "Prepares inboxes and validates externally generated MP4 shot results.", "MVP"],
    ["RiskAgent", "Checks similarity, rating risk, and promo language risk.", "MVP"],
    ["AnimaticAgent", "Renders storyboard boards and MP4 animatics from approved shot tables.", "MVP"],
    ["ReportAgent", "Generates daily, weekly, sample-status, and risk reports.", "Planned"],
]


BUDGET = [
    ["Storyboard and animatic", 15000],
    ["Character and setting design", 18000],
    ["Action design and key animation", 30000],
    ["Animation direction, cleanup, inbetweens", 18000],
    ["Background and color", 12000],
    ["Compositing and effects", 15000],
    ["Sound and temp music", 6000],
    ["Production management and reserve", 6000],
]


RISKS = [
    ["Character consistency", "Generated visual assets can drift; reference library and approval are required."],
    ["Poison membrane effect", "Mizumoni membrane is a core sample selling point; cheap visuals hurt financing."],
    ["Originality boundary", "Generated visuals require similarity and promo-language checks."],
    ["Budget trial waste", "Generation and comp test counts must be tracked."],
    ["Rating risk", "Face-skinning, parasites, experiments, and child harm need international-version alternatives."],
]


def summarize_segment(segment: str) -> dict:
    manifest_path = ANIME_PROJECT / "episode_segments" / segment / "manifest.json"
    manifest = read_json(manifest_path, {})
    replacement_path = ANIME_PROJECT / "episode_segments" / segment / "manifest_with_replacements.json"
    replacement = read_json(replacement_path, {})
    local_polish_path = ANIME_PROJECT / "episode_segments" / segment / "manifest_with_local_polish.json"
    local_polish = read_json(local_polish_path, {})
    shot_videos = manifest.get("shot_videos", [])
    existing_shots = sum(1 for video in shot_videos if file_status(video)["exists"])
    replacement_video = replacement.get("video") or ""
    replacement_count = sum(1 for shot in replacement.get("shots", []) if shot.get("replacement"))
    if not replacement_count:
        replacement_count = len(replacement.get("replacement_sources", []))
    if not replacement_count and replacement.get("replacements"):
        replacement_count = len(replacement.get("replacements", []))
    return {
        "name": segment,
        "manifest": str(manifest_path.relative_to(WORKSPACE)),
        "shot_count": manifest.get("shot_count", len(shot_videos)),
        "existing_shot_count": existing_shots,
        "duration_seconds": manifest.get("duration_seconds", 0),
        "width": manifest.get("width", 0),
        "height": manifest.get("height", 0),
        "fps": manifest.get("fps", 0),
        "active_mode": manifest.get("active_mode", ""),
        "review_status": manifest.get("review_status", ""),
        "video": file_status(manifest.get("video")),
        "audio": file_status(manifest.get("audio")),
        "replacement_manifest": str(replacement_path.relative_to(WORKSPACE)) if replacement_path.exists() else "",
        "replacement_video": file_status(replacement_video),
        "replacement_count": replacement_count,
        "local_polish_manifest": str(local_polish_path.relative_to(WORKSPACE)) if local_polish_path.exists() else "",
        "local_polish_video": file_status(local_polish.get("video")),
        "local_polish_replacement_count": sum(1 for shot in local_polish.get("shots", []) if shot.get("replacement")),
    }


def summarize_master() -> dict:
    manifest_path = ANIME_PROJECT / "episode_segments" / "master_preview" / "manifest.json"
    replacement_path = ANIME_PROJECT / "episode_segments" / "master_preview" / "manifest_with_replacements.json"
    local_polish_path = ANIME_PROJECT / "episode_segments" / "master_preview" / "manifest_with_local_polish.json"
    manifest = read_json(manifest_path, {})
    replacement = read_json(replacement_path, {})
    local_polish = read_json(local_polish_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "replacement_manifest": str(replacement_path.relative_to(WORKSPACE)) if replacement_path.exists() else "",
        "local_polish_manifest": str(local_polish_path.relative_to(WORKSPACE)) if local_polish_path.exists() else "",
        "segments": manifest.get("segments", []),
        "shot_count": manifest.get("shot_count", 0),
        "duration_seconds": manifest.get("duration_seconds", 0),
        "width": manifest.get("width", 0),
        "height": manifest.get("height", 0),
        "fps": manifest.get("fps", 0),
        "review_status": manifest.get("review_status", replacement.get("status", "")),
        "video": file_status(manifest.get("video")),
        "replacement_video": file_status(replacement.get("video")),
        "replacement_status": replacement.get("status", ""),
        "local_polish_video": file_status(local_polish.get("video")),
        "local_polish_status": local_polish.get("status", ""),
        "local_polish_duration_seconds": local_polish.get("duration_seconds", 0),
    }


def summarize_provider_pipeline() -> dict:
    registry_path = ANIME_PROJECT / "pipeline" / "provider_registry.json"
    provider_summary_path = ANIME_PROJECT / "pipeline" / "provider_runs" / "provider_run_summary.json"
    registry = read_json(registry_path, {})
    provider_summary = read_json(provider_summary_path, {})
    providers = registry.get("providers", {})
    external_providers = [
        name for name, spec in providers.items() if name != "local_2d_fallback" and spec.get("status")
    ]
    return {
        "registry": str(registry_path.relative_to(WORKSPACE)) if registry_path.exists() else "",
        "summary": str(provider_summary_path.relative_to(WORKSPACE)) if provider_summary_path.exists() else "",
        "delivery_standard": registry.get("delivery_standard", {}),
        "provider_count": len(providers),
        "external_provider_count": len(external_providers),
        "providers": [
            {
                "name": name,
                "status": spec.get("status", ""),
                "role": spec.get("role", []),
                "adapter": spec.get("adapter", ""),
            }
            for name, spec in providers.items()
        ],
        "dry_run_mode": provider_summary.get("mode", ""),
        "segments": provider_summary.get("segments", []),
        "jobs_processed": provider_summary.get("total_jobs_processed", 0),
        "request_packets": provider_summary.get("total_request_packets", 0),
        "next_step": provider_summary.get("next_step", ""),
    }


def summarize_external_results() -> dict:
    expected_path = ANIME_PROJECT / "pipeline" / "external_results" / "manifests" / "expected_external_results.json"
    validated_path = ANIME_PROJECT / "pipeline" / "external_results" / "manifests" / "validated_external_results.json"
    expected = read_json(expected_path, {})
    validated = read_json(validated_path, {})
    return {
        "expected_manifest": str(expected_path.relative_to(WORKSPACE)) if expected_path.exists() else "",
        "validated_manifest": str(validated_path.relative_to(WORKSPACE)) if validated_path.exists() else "",
        "inbox": expected.get("inbox", validated.get("inbox", "")),
        "provider_count": len(expected.get("providers", [])),
        "expected_result_count": expected.get("expected_result_count", 0),
        "accepted_count": validated.get("accepted_count", 0),
        "rejected_count": validated.get("rejected_count", 0),
        "unknown_count": validated.get("unknown_count", 0),
        "next_step": validated.get("next_step", ""),
    }


def summarize_external_reviews() -> dict:
    review_path = ANIME_PROJECT / "pipeline" / "external_reviews" / "approved_external_results.json"
    review = read_json(review_path, {})
    return {
        "manifest": str(review_path.relative_to(WORKSPACE)) if review_path.exists() else "",
        "stage": review.get("stage", ""),
        "reviewed_count": review.get("reviewed_count", 0),
        "approved_count": review.get("approved_count", 0),
        "returned_count": review.get("returned_count", 0),
        "report": review.get("report", ""),
        "reviews": review.get("reviews", []),
        "next_step": review.get("next_step", ""),
    }


def summarize_adapter_runs() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "adapter_runs" / "code_video_adapter_manifest.json"
    manifest = read_json(manifest_path, {})
    renders = manifest.get("renders", [])
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "stage": manifest.get("stage", ""),
        "mode": manifest.get("mode", ""),
        "provider": manifest.get("provider", ""),
        "rendered_count": manifest.get("rendered_count", len(renders)),
        "external_inbox": manifest.get("external_inbox", ""),
        "outputs_ready": sum(1 for item in renders if file_status(item.get("output"))["exists"]),
        "renders": renders,
        "next_step": manifest.get("next_step", ""),
    }


def summarize_external_video_runs() -> dict:
    summary_path = ANIME_PROJECT / "pipeline" / "adapter_runs" / "external_video" / "summary_manifest.json"
    assembly_path = ANIME_PROJECT / "pipeline" / "adapter_runs" / "external_video" / "chunk_assembly_manifest.json"
    summary = read_json(summary_path, {})
    assembly = read_json(assembly_path, {})
    manifests = []
    for raw_path in summary.get("manifests", []):
        manifest = read_json(project_path(raw_path) or Path(), {})
        readiness = manifest.get("readiness", {})
        manifests.append(
            {
                "provider": manifest.get("provider", ""),
                "status": manifest.get("status", ""),
                "submission_count": manifest.get("submission_count", 0),
                "packet_count": manifest.get("packet_count", 0),
                "ready_for_api_submit": readiness.get("ready_for_api_submit", False),
                "has_endpoint": readiness.get("has_endpoint", False),
                "has_token": readiness.get("has_token", False),
                "manual_submission_packet": manifest.get("manual_submission_packet", ""),
            }
        )
    return {
        "manifest": str(summary_path.relative_to(WORKSPACE)) if summary_path.exists() else "",
        "stage": summary.get("stage", ""),
        "mode": summary.get("mode", ""),
        "provider_count": summary.get("provider_count", 0),
        "ready_provider_count": summary.get("ready_provider_count", 0),
        "blocked_provider_count": summary.get("blocked_provider_count", 0),
        "total_packet_count": summary.get("total_packet_count", 0),
        "total_submission_count": summary.get("total_submission_count", 0),
        "providers": manifests,
        "assembly": {
            "manifest": str(assembly_path.relative_to(WORKSPACE)) if assembly_path.exists() else "",
            "assembled_count": assembly.get("assembled_count", 0),
            "waiting_count": assembly.get("waiting_count", 0),
            "next_step": assembly.get("next_step", ""),
        },
        "next_step": summary.get("next_step", ""),
    }


def summarize_submit_gate() -> dict:
    gate_path = ANIME_PROJECT / "pipeline" / "submit_gate" / "external_submit_gate_manifest.json"
    gate = read_json(gate_path, {})
    return {
        "manifest": str(gate_path.relative_to(WORKSPACE)) if gate_path.exists() else "",
        "stage": gate.get("stage", ""),
        "mode": gate.get("mode", ""),
        "provider_count": gate.get("provider_count", 0),
        "allowed_provider_count": gate.get("allowed_provider_count", 0),
        "blocked_provider_count": gate.get("blocked_provider_count", 0),
        "total_submission_count": gate.get("total_submission_count", 0),
        "total_estimated_cost_usd": gate.get("total_estimated_cost_usd", 0),
        "approval_request": gate.get("approval_request", ""),
        "providers": gate.get("providers", []),
        "next_step": gate.get("next_step", ""),
    }


def summarize_provider_submit_runs() -> dict:
    submit_path = ANIME_PROJECT / "pipeline" / "submit_runs" / "external_video" / "submit_run_manifest.json"
    submit = read_json(submit_path, {})
    return {
        "manifest": str(submit_path.relative_to(WORKSPACE)) if submit_path.exists() else "",
        "stage": submit.get("stage", ""),
        "mode": submit.get("mode", ""),
        "allowed_provider_count": submit.get("allowed_provider_count", 0),
        "blocked_provider_count": submit.get("blocked_provider_count", 0),
        "submitted_count": submit.get("submitted_count", 0),
        "failed_count": submit.get("failed_count", 0),
        "blocked_providers": submit.get("blocked_providers", []),
        "provider_runs": submit.get("provider_runs", []),
        "next_step": submit.get("next_step", ""),
    }


def summarize_provider_poll_runs() -> dict:
    poll_path = ANIME_PROJECT / "pipeline" / "poll_runs" / "external_video" / "poll_run_manifest.json"
    poll = read_json(poll_path, {})
    return {
        "manifest": str(poll_path.relative_to(WORKSPACE)) if poll_path.exists() else "",
        "stage": poll.get("stage", ""),
        "mode": poll.get("mode", ""),
        "submitted_item_count": poll.get("submitted_item_count", 0),
        "ready_for_download_count": poll.get("ready_for_download_count", 0),
        "pending_count": poll.get("pending_count", 0),
        "downloaded_count": poll.get("downloaded_count", 0),
        "poll_results": poll.get("poll_results", []),
        "next_step": poll.get("next_step", ""),
    }


def summarize_mcp_video_gateway() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "mcp_video_gateway" / "mcp_video_gateway_manifest.json"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "stage": manifest.get("stage", ""),
        "mode": manifest.get("mode", ""),
        "provider_count": manifest.get("provider_count", 0),
        "dispatch_count": manifest.get("dispatch_count", 0),
        "submitted_count": manifest.get("submitted_count", 0),
        "prepared_count": manifest.get("prepared_count", 0),
        "blocked_count": manifest.get("blocked_count", 0),
        "failed_count": manifest.get("failed_count", 0),
        "dispatch_queue": manifest.get("dispatch_queue", ""),
        "report": manifest.get("report", ""),
        "providers": manifest.get("providers", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_replacements() -> dict:
    candidate_path = ANIME_PROJECT / "pipeline" / "replacements" / "candidate_manifest.json"
    apply_path = ANIME_PROJECT / "pipeline" / "replacements" / "apply_manifest.json"
    review_path = ANIME_PROJECT / "pipeline" / "replacements" / "replacement_review.md"
    candidates = read_json(candidate_path, {})
    applied = read_json(apply_path, {})
    segments = applied.get("segments", [])
    return {
        "candidate_manifest": str(candidate_path.relative_to(WORKSPACE)) if candidate_path.exists() else "",
        "apply_manifest": str(apply_path.relative_to(WORKSPACE)) if apply_path.exists() else "",
        "review_report": str(review_path.relative_to(WORKSPACE)) if review_path.exists() else "",
        "candidate_count": candidates.get("replacement_count", len(candidates.get("replacements", []))),
        "applied_segment_count": len(segments),
        "applied_replacement_count": sum(segment.get("replacement_count", 0) for segment in segments),
        "status": applied.get("status", ""),
        "replacements": candidates.get("replacements", []),
    }


def summarize_acceptance() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "acceptance" / "master_acceptance_manifest.json"
    report_path = ANIME_PROJECT / "pipeline" / "acceptance" / "master_acceptance_report.md"
    manifest = read_json(manifest_path, {})
    checklist = manifest.get("checklist", {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "final_release_ready": manifest.get("final_release_ready", False),
        "passed_count": checklist.get("passed_count", 0),
        "failed_count": checklist.get("failed_count", 0),
        "checks": checklist.get("checks", {}),
        "master": manifest.get("master", {}),
        "risk_status": manifest.get("risk_rules", {}).get("status", ""),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_director_review() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "director_review" / "director_risk_review_manifest.json"
    report_path = ANIME_PROJECT / "pipeline" / "director_review" / "director_risk_review.md"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "final_release_ready": manifest.get("final_release_ready", False),
        "reviewed_keyframe_count": manifest.get("reviewed_keyframe_count", 0),
        "nonblank_keyframe_count": manifest.get("nonblank_keyframe_count", 0),
        "replacement_keyframe_count": manifest.get("replacement_keyframe_count", 0),
        "risk_keyframe_count": manifest.get("risk_keyframe_count", 0),
        "contact_sheet": manifest.get("contact_sheet", ""),
        "keyframes": manifest.get("keyframes", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_director_review_v02() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "director_review_v02" / "director_risk_review_v02_manifest.json"
    report_path = ANIME_PROJECT / "pipeline" / "director_review_v02" / "director_risk_review_v02.md"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "final_release_ready": manifest.get("final_release_ready", False),
        "reviewed_keyframe_count": manifest.get("reviewed_keyframe_count", 0),
        "nonblank_keyframe_count": manifest.get("nonblank_keyframe_count", 0),
        "replacement_keyframe_count": manifest.get("replacement_keyframe_count", 0),
        "risk_keyframe_count": manifest.get("risk_keyframe_count", 0),
        "contact_sheet": manifest.get("contact_sheet", ""),
        "keyframes": manifest.get("keyframes", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_producer_demo_package() -> dict:
    manifest_path = ANIME_PROJECT / "deliverables" / "producer_demo_v01" / "producer_demo_manifest.json"
    readme_path = ANIME_PROJECT / "deliverables" / "producer_demo_v01" / "README_PRODUCER_DEMO.md"
    manifest = read_json(manifest_path, {})
    zip_info = manifest.get("zip", {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "readme": str(readme_path.relative_to(WORKSPACE)) if readme_path.exists() else manifest.get("readme", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "final_release_ready": manifest.get("final_release_ready", False),
        "package_dir": manifest.get("package_dir", ""),
        "artifact_count": manifest.get("artifact_count", 0),
        "zip": file_status(zip_info.get("path", "")),
        "acceptance_decision": manifest.get("acceptance", {}).get("decision", ""),
        "director_review_decision": manifest.get("director_review", {}).get("decision", ""),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_producer_demo_v02_package() -> dict:
    manifest_path = ANIME_PROJECT / "deliverables" / "producer_demo_v02" / "producer_demo_v02_manifest.json"
    readme_path = ANIME_PROJECT / "deliverables" / "producer_demo_v02" / "README_PRODUCER_DEMO_V02.md"
    manifest = read_json(manifest_path, {})
    zip_info = manifest.get("zip", {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "readme": str(readme_path.relative_to(WORKSPACE)) if readme_path.exists() else manifest.get("readme", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "final_release_ready": manifest.get("final_release_ready", False),
        "package_dir": manifest.get("package_dir", ""),
        "zip": file_status(zip_info.get("path")) if zip_info.get("path") else {},
        "master_video": manifest.get("master_video", ""),
        "artifact_count": manifest.get("artifact_count", 0),
        "promoted_count": manifest.get("local_polish_promotion", {}).get("promoted_count", 0),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_current_demo() -> dict:
    manifest_path = ANIME_PROJECT / "deliverables" / "current_demo" / "current_demo_manifest.json"
    readme_path = ANIME_PROJECT / "deliverables" / "current_demo" / "CURRENT_PRODUCER_DEMO.md"
    registry_path = ANIME_PROJECT / "deliverables" / "demo_version_registry.json"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "readme": str(readme_path.relative_to(WORKSPACE)) if readme_path.exists() else manifest.get("readme", ""),
        "registry": str(registry_path.relative_to(WORKSPACE)) if registry_path.exists() else manifest.get("registry", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "current_version": manifest.get("current_version", ""),
        "current_zip": file_status(manifest.get("current_zip")),
        "current_video": file_status(manifest.get("current_video")),
        "zip_entry_count": manifest.get("zip_entry_count", 0),
        "final_release_ready": manifest.get("final_release_ready", False),
        "source_package_decision": manifest.get("source_package", {}).get("decision", ""),
        "director_review_decision": manifest.get("director_review_v02", {}).get("decision", ""),
        "promoted_count": manifest.get("local_polish_promotion", {}).get("promoted_count", 0),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_polish_queue() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "polish_queue" / "polish_queue_manifest.json"
    report_path = ANIME_PROJECT / "pipeline" / "polish_queue" / "polish_work_order.md"
    packets_path = ANIME_PROJECT / "pipeline" / "polish_queue" / "provider_handoff_packets.jsonl"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "provider_packets": file_status(str(packets_path.relative_to(WORKSPACE)) if packets_path.exists() else manifest.get("provider_packets", "")),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "final_release_ready": manifest.get("final_release_ready", False),
        "queue_count": manifest.get("queue_count", 0),
        "provider_packet_count": manifest.get("provider_packet_count", 0),
        "estimated_external_cost_usd": manifest.get("estimated_external_cost_usd", 0),
        "registry_provider_count": manifest.get("registry_provider_count", 0),
        "submit_allowed_provider_count": manifest.get("submit_gate", {}).get("allowed_provider_count", 0),
        "submit_blocked_provider_count": manifest.get("submit_gate", {}).get("blocked_provider_count", 0),
        "queue": manifest.get("queue", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_provider_launch() -> dict:
    manifest_path = (
        ANIME_PROJECT
        / "pipeline"
        / "provider_launch"
        / "current_demo_hq_v01"
        / "high_quality_provider_launch_manifest.json"
    )
    report_path = (
        ANIME_PROJECT
        / "pipeline"
        / "provider_launch"
        / "current_demo_hq_v01"
        / "high_quality_provider_launch_report.md"
    )
    manifest = read_json(manifest_path, {})
    handoff_manifest_path = (
        ANIME_PROJECT
        / "deliverables"
        / "provider_launch"
        / "current_demo_hq_v01"
        / "current_demo_hq_provider_handoff_manifest.json"
    )
    handoff = read_json(handoff_manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "decision": manifest.get("decision", "not_run"),
        "selected_shot_count": manifest.get("selected_shot_count", 0),
        "selected_provider_count": manifest.get("selected_provider_count", 0),
        "estimated_first_pass_cost_usd": manifest.get("estimated_first_pass_cost_usd", 0),
        "config_template": manifest.get("config_template", ""),
        "env_example": manifest.get("env_example", ""),
        "selected_rows_jsonl": manifest.get("selected_rows_jsonl", ""),
        "provider_packets": manifest.get("provider_packets", []),
        "handoff_manifest": str(handoff_manifest_path.relative_to(WORKSPACE)) if handoff_manifest_path.exists() else "",
        "handoff_decision": handoff.get("decision", "not_run"),
        "handoff_zip": file_status(handoff.get("zip", {}).get("path")),
        "handoff_artifact_count": handoff.get("artifact_count", 0),
        "handoff_zip_entry_count": handoff.get("zip", {}).get("entry_count", 0),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_provider_returns() -> dict:
    manifest_path = (
        ANIME_PROJECT
        / "pipeline"
        / "provider_returns"
        / "current_demo_hq_v01"
        / "hq_provider_return_sim_manifest.json"
    )
    report_path = (
        ANIME_PROJECT
        / "pipeline"
        / "provider_returns"
        / "current_demo_hq_v01"
        / "hq_provider_return_sim_report.md"
    )
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "mode": manifest.get("mode", ""),
        "decision": manifest.get("decision", "not_run"),
        "generated_count": manifest.get("generated_count", 0),
        "accepted_count": manifest.get("accepted_count", 0),
        "rejected_count": manifest.get("rejected_count", 0),
        "provider_counts": manifest.get("provider_counts", {}),
        "contact_sheet": manifest.get("contact_sheet", ""),
        "returns": manifest.get("returns", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_review_closure() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "review_closure" / "production_review_closure_manifest.json"
    report_path = ANIME_PROJECT / "pipeline" / "review_closure" / "production_review_closure_report.md"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "mode": manifest.get("mode", ""),
        "decision": manifest.get("decision", "not_run"),
        "approved_count": manifest.get("approved_count", 0),
        "kept_open_count": manifest.get("kept_open_count", 0),
        "remaining_needs_review_count": manifest.get("remaining_needs_review_count", 0),
        "remaining_returned_count": manifest.get("remaining_returned_count", 0),
        "remaining_pending_count": manifest.get("remaining_pending_count", 0),
        "kept_open": manifest.get("kept_open", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_local_polish() -> dict:
    manifest_path = ANIME_PROJECT / "pipeline" / "polish_outputs" / "local_remotion" / "local_polish_render_manifest.json"
    report_path = ANIME_PROJECT / "pipeline" / "polish_outputs" / "local_remotion" / "local_polish_render_report.md"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "mode": manifest.get("mode", ""),
        "decision": manifest.get("decision", "not_run"),
        "rendered_count": manifest.get("rendered_count", 0),
        "accepted_count": manifest.get("accepted_count", 0),
        "rejected_count": manifest.get("rejected_count", 0),
        "contact_sheet": manifest.get("contact_sheet", ""),
        "renders": manifest.get("renders", []),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_local_polish_promotion() -> dict:
    manifest_path = (
        ANIME_PROJECT
        / "pipeline"
        / "polish_outputs"
        / "local_remotion"
        / "promotion"
        / "local_polish_promotion_manifest.json"
    )
    report_path = (
        ANIME_PROJECT
        / "pipeline"
        / "polish_outputs"
        / "local_remotion"
        / "promotion"
        / "local_polish_promotion_report.md"
    )
    manifest = read_json(manifest_path, {})
    return {
        "manifest": str(manifest_path.relative_to(WORKSPACE)) if manifest_path.exists() else "",
        "report": str(report_path.relative_to(WORKSPACE)) if report_path.exists() else manifest.get("report", ""),
        "stage": manifest.get("stage", ""),
        "mode": manifest.get("mode", ""),
        "decision": manifest.get("decision", "not_run"),
        "promoted_count": manifest.get("promoted_count", 0),
        "segments": manifest.get("segments", []),
        "master_manifest": manifest.get("master_manifest", ""),
        "master_video": file_status(manifest.get("master_video")),
        "next_step": manifest.get("next_step", ""),
    }


def pipeline_status() -> dict:
    segments = ["onsen_01_sample", "act2_01_sample"]
    return {
        "stage": "complete_flow_mvp_ready_for_external_provider_integration",
        "master": summarize_master(),
        "segments": [summarize_segment(segment) for segment in segments],
        "providers": summarize_provider_pipeline(),
        "adapter_runs": summarize_adapter_runs(),
        "external_video_runs": summarize_external_video_runs(),
        "submit_gate": summarize_submit_gate(),
        "provider_submit": summarize_provider_submit_runs(),
        "provider_poll": summarize_provider_poll_runs(),
        "mcp_video_gateway": summarize_mcp_video_gateway(),
        "external_results": summarize_external_results(),
        "external_reviews": summarize_external_reviews(),
        "replacements": summarize_replacements(),
        "acceptance": summarize_acceptance(),
        "director_review": summarize_director_review(),
        "director_review_v02": summarize_director_review_v02(),
        "producer_demo_package": summarize_producer_demo_package(),
        "producer_demo_package_v02": summarize_producer_demo_v02_package(),
        "current_demo": summarize_current_demo(),
        "polish_queue": summarize_polish_queue(),
        "provider_launch": summarize_provider_launch(),
        "provider_returns": summarize_provider_returns(),
        "review_closure": summarize_review_closure(),
        "local_polish": summarize_local_polish(),
        "local_polish_promotion": summarize_local_polish_promotion(),
        "artifacts": [
            "anime_project\\episode_segments\\master_preview\\final\\kage_preview_onsen_plus_act2.mp4",
            "anime_project\\episode_segments\\master_preview\\final\\kage_preview_with_replacements.mp4",
            "anime_project\\episode_segments\\master_preview\\final\\kage_preview_with_local_polish.mp4",
            "anime_project\\pipeline\\provider_registry.json",
            "anime_project\\pipeline\\external_results\\README.md",
            "anime_project\\pipeline\\acceptance\\master_acceptance_report.md",
            "anime_project\\pipeline\\director_review\\director_risk_review.md",
            "anime_project\\pipeline\\director_review_v02\\director_risk_review_v02.md",
            "anime_project\\deliverables\\producer_demo_v01.zip",
            "anime_project\\deliverables\\producer_demo_v02.zip",
            "anime_project\\deliverables\\current_demo\\current_producer_demo.zip",
            "anime_project\\deliverables\\current_demo\\video\\kage_current_demo.mp4",
            "anime_project\\pipeline\\polish_queue\\polish_work_order.md",
            "anime_project\\pipeline\\provider_launch\\current_demo_hq_v01\\high_quality_provider_launch_report.md",
            "anime_project\\deliverables\\current_demo_hq_provider_handoff_v01.zip",
            "anime_project\\pipeline\\provider_returns\\current_demo_hq_v01\\hq_provider_return_sim_report.md",
            "anime_project\\pipeline\\review_closure\\production_review_closure_report.md",
            "anime_project\\pipeline\\polish_outputs\\local_remotion\\local_polish_render_report.md",
            "anime_project\\pipeline\\polish_outputs\\local_remotion\\promotion\\local_polish_promotion_report.md",
        ],
    }


DEFAULT_TASKS = [
    {
        "id": "TASK-001",
        "agent": "WriterAgent",
        "title": "Expand Act II upper script scenes",
        "prompt": "Continue from Act I into abandoned mine, Iron Centipede, swamp village, Hirumaru, and Chiyo.",
        "status": "Queued",
        "priority": "High",
        "review": "Pending",
        "output": "",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    },
    {
        "id": "TASK-002",
        "agent": "RiskAgent",
        "title": "Check sample sequence rating risks",
        "prompt": "Review Rainy Night Onsen shot list for V2/V3/M/C rating risk markers and international cut options.",
        "status": "Queued",
        "priority": "Medium",
        "review": "Pending",
        "output": "",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    },
]


def load_tasks() -> list[dict]:
    tasks = read_json(TASKS_FILE, None)
    if tasks is None:
        write_json(TASKS_FILE, DEFAULT_TASKS)
        return DEFAULT_TASKS
    return tasks


def save_tasks(tasks: list[dict]) -> None:
    write_json(TASKS_FILE, tasks)


def next_task_id(tasks: list[dict]) -> str:
    max_id = 0
    for task in tasks:
        raw = str(task.get("id", "TASK-000")).replace("TASK-", "")
        if raw.isdigit():
            max_id = max(max_id, int(raw))
    return f"TASK-{max_id + 1:03d}"


def build_act_two_upper_draft(task: dict) -> str:
    return f"""# WriterAgent Output: 第二幕上草稿

任务：{task.get("title", "")}

提示：{task.get("prompt", "")}

## 目标

承接第一幕结尾“这是旧账”，推进废矿、铁蜈蚣、沼泽村、蛭丸、千代之死，并把凛藏对鸢的判断从“雇主/麻烦”推向“她确实在为活人行动”。

## 场 07 外景，废矿入口，雨后清晨

雨停了，山雾还贴在树根上。

鸢沿着货车车辙走。泥里混着黑色矿粉，像烧过的药渣。凛藏走在她后面，始终保持三步距离。

鸢停下，蹲下，用银针挑起一点矿粉。

鸢：药炉要吃这种石头。

凛藏：炉子吃石头，人吃药。最后死的是谁？

鸢没有抬头。

鸢：通常是没有名字的人。

矿道口挂着旧封条。封条上有幕府官印，官印下方另有一道极细的眼形暗记。

凛藏看见暗记，伸手去摸。

鸢：你认得？

凛藏：影目付送货时用的路标。

矿道深处传来金属拖地声。

不是一声。

是一节一节。

## 场 08 内景，废矿深处

矿道狭窄，长刀无法完全展开。

凛藏把长刀推回鞘中，只留短刀在手。鸢把药箱背到胸前，另一手握住短弩。

墙壁上有抓痕。抓痕不是向外逃，而是向矿道更深处爬。

一名矿工尸体倒挂在支架上。背部被什么东西切成整齐的节段。

鸢刚要检查，尸体忽然被拖入黑暗。

铁蜈蚣从顶壁爬出。

它仍像人，但脊椎被铁节拉长，背后链刃一节节展开。矿尘从它身上落下，像一场小雨。

铁蜈蚣冲向鸢。

凛藏踏前半步，短刀切向它手腕。

刀切进肉里，却被铁箍挡住。

铁蜈蚣贴墙转向，链刃扫过。凛藏后仰，斗笠边缘被削掉一片。

鸢射出弩箭。

弩箭没有射铁蜈蚣，而是射断矿灯吊绳。

矿灯坠落，火油沿地面流开。

凛藏看她一眼。

鸢：你说过，普通刀伤未必有用。

凛藏把短刀反握，脚尖勾住矿车制动杆。

铁蜈蚣第二次冲来。

凛藏没有迎击。他拉开矿车，让铁蜈蚣追进支架下方。鸢把药粉撒进火油，火焰瞬间变白，照出顶上腐朽横梁。

凛藏斩断支撑绳。

矿道塌了一半。

铁蜈蚣被压住，链刃还在乱甩。它伸出像人一样的手，抓住凛藏脚踝。

凛藏看着那只手。

手腕内侧有旧影目付烧印。

凛藏一刀切断手腕。

塌方彻底落下。

## 场 09 内景，矿道塌方后

灰尘落定。

鸢在塌方边缘找到一只陶罐碎片。碎片内壁附着黑红色药痕，遇到空气后轻微发热。

鸢用布包住碎片，指尖还是被烫到。

凛藏抓住她手腕。

她的皮肤没有发黑，只是血管短暂泛出淡色纹路。

凛藏：你到底是什么？

鸢抽回手。

鸢：现在还不是你能收钱买到的答案。

矿道外传来乌鸦声。

两人离开时，凛藏回头看了一眼塌方。铁链摩擦声已经停了。

## 场 10 外景，沼泽村外围，黄昏

沼泽村没有狗叫。

也没有炊烟。

村口立着封锁木牌，上面写着“黑热”。牌子下方堆着旧草鞋和破碗，像逃难的人走到这里就被迫脱下了身份。

凛藏：绕过去。

鸢已经走进村口。

凛藏：你想死？

鸢：如果这里还有活人，绕过去的人也会死。

凛藏没有跟上。

鸢回头。

鸢：你可以在这里等。交易还没到必须讲义气的时候。

她继续往里走。

凛藏站了一息，跟上。

## 场 11 内景/外景，沼泽村

村屋里全是潮气。

墙上贴着药符，药符已经被黑色水痕泡烂。榻榻米下有轻微蠕动声。

鸢听见声音，掀开角落的草席。

一个女孩缩在那里，八九岁，抱着破布娃娃。她额头发黑，呼吸热得像贴近炉口。

鸢：千代？

女孩没有回答。

凛藏看向门外。

泥水里有东西靠近。

蛭丸从尸堆下站起来。

它瘦长，湿布包在背后蠕动。腹部黑热斑纹一开一合，像另一张嘴在呼吸。

蛭丸：药师。把孩子留下。

鸢把千代护到身后。

凛藏：她不是你的病人。

蛭丸笑了，笑声像泥水冒泡。

蛭丸割开自己的手臂。

伤口里不是血先流出来，而是一条条湿亮的蛭。

凛藏砍断第一批蛭，刀刃立刻发黑。

鸢把药粉撒在刀上。

鸢：再砍。

凛藏：你命令人的口气越来越顺。

鸢：你收了钱。

蛭丸扑来。

凛藏用门板挡住它，门板瞬间爬满寄生蛭。鸢点燃药烟，白烟贴着地面滚过，蛭群缩回泥水。

蛭丸吸食一具尸体残血，伤口重新愈合。

凛藏看明白了。

他不再攻击蛭丸身体，而是斩断它通向尸堆的退路。鸢把盐药撒进泥水，蛭丸脚下开始冒白泡。

凛藏三步近身。

短刀刺入蛭丸喉下。

蛭丸抓住凛藏手腕，低声说：

蛭丸：你也热。你也是炉里出来的。

凛藏眼神一沉。

他把短刀横拉。

蛭丸倒进泥水，身体还在再生。

鸢把最后一包药粉塞进它伤口。

这一次，再生停止了。

## 场 12 内景，村屋，夜

千代的呼吸越来越轻。

鸢跪在她身边，割开自己的指尖，把血滴进药水里。

药水短暂变清。

千代睁开眼。

千代：娘呢？

鸢没有回答。

凛藏站在门边，看着外面的尸堆。

鸢把药水喂给千代。黑热斑纹退下去一点，又很快爬回来。

鸢再割深一点。

凛藏抓住她手腕。

凛藏：够了。

鸢：还没有。

凛藏：她救不回来。

鸢看着他，眼里第一次有怒意。

鸢：你怎么知道？

凛藏：因为这里不是病房，是试验场。

千代的手松开。破布娃娃掉在地上。

鸢停住。

屋外的雨又开始下。

很小。

像有人在远处筛灰。

## 场 13 外景，沼泽村夜

鸢把千代埋在村口，没有立木牌。

凛藏站在远处。

鸢：你刚才说试验场。

凛藏：这种死法，我见过。

鸢：感染村？

凛藏没有回答。

鸢：你不是唯一一个被那件事留下来的人。

凛藏：我留下来的只有刀。

鸢：那就看你下一次把刀落在哪里。

凛藏看向她。

这是他第一次真正看她，而不是看她身上的任务。

## 场 14 外景，荒寺外，黎明

荒寺在雾里。

寺门半塌，门前挤着灾民和流浪艺人。有人烧水，有人包扎伤口，有人用破布盖住脸上的黑斑。

远处传来琵琶声。

每拨一下，灾民们的动作就慢一分。

鸢停下脚步。

凛藏按住刀。

琵琶声又响。

这一次，凛藏脚下的石阶像向左倾斜。

鸢捂住耳朵，低声说：

鸢：别信你的脚。

凛藏：那信什么？

鸢看向荒寺深处。

鸢：信刀落地的声音。

## 审查备注

- V2：铁蜈蚣与蛭丸战斗。
- V3/C：千代死亡，必须克制，避免过程猎奇。
- M：黑热药痕、鸢血脉、人体实验暗示。
- 制作重点：废矿狭窄空间、沼泽泥水和寄生蛭数量必须可控。
"""


def build_act_two_upper_revision(task: dict) -> str:
    return f"""# WriterAgent Output: 第二幕上返修稿 v0.2

任务：{task.get("title", "")}

返修依据：DirectorAgent 审查要求压缩废矿战、减少旧药/药炉重复解释、重写千代死亡段、降低荒寺台词文学感，并补充尺度标记。

## 返修说明

本版保留 v0.1 的场次骨架，但做四项调整：

1. 废矿战压缩为更短的环境战，保留矿灯、白火、塌方和影目付烧印。
2. 蛭丸不再直接解释“炉里出来”，改为通过凛藏体温和伤口反应暗示旧药。
3. 千代死亡段减少对白，改为鸢的动作和药水变化承载情绪。
4. 荒寺钩子降低文学感，改成更硬的动作判断。

---

## 场 07 外景，废矿入口，雨后清晨

雨停了。

山雾贴着树根，货车车辙一路通向废矿。泥里混着黑色矿粉，被晨光照出细碎的绿。

鸢蹲下，用银针挑起一点矿粉。针尖很快发热。

鸢：药炉用这种石头稳毒。

凛藏看向矿口。

矿口旧封条被雨水泡烂，幕府官印下方藏着一道极细的眼形暗记。

凛藏伸手摸了一下。

鸢：影目付？

凛藏：送货路标。

矿道深处传来金属拖地声。

一节。

又一节。

凛藏把长刀推回鞘中，只留短刀。

尺度标记：M。

---

## 场 08 内景，废矿深处

矿道窄得无法挥长刀。

墙上有爬行抓痕。抓痕不是向外逃，而是往更深处去。

一具矿工尸体倒挂在木架上。背部被切成整齐节段。

鸢刚靠近，尸体被拖入黑暗。

铁蜈蚣从顶壁落下。

它仍有人的头和手，背部却被铁节拉长，链刃沿脊椎展开。矿尘从它身上落下，像一场小雨。

铁蜈蚣冲向鸢。

凛藏踏前半步，短刀切向它手腕。

刀被铁箍挡住。

铁蜈蚣贴墙转向，链刃扫过。凛藏后仰，斗笠边缘被削掉一片。

鸢射断矿灯吊绳。

矿灯坠落，火油沿地面流开。

她把药粉撒进火油。

白火一闪，照出顶上腐朽横梁。

凛藏不再追击。他拉开矿车，让铁蜈蚣追进支架下方。

第二次链刃扫来时，凛藏斩断支撑绳。

矿道塌下一半。

铁蜈蚣被压住，链刃还在乱甩。它伸出一只像人一样的手，抓住凛藏脚踝。

手腕内侧有旧影目付烧印。

凛藏停了一息。

然后切断那只手。

塌方彻底落下。

没有胜利声。

只有矿尘和铁节最后一次摩擦。

尺度标记：V2、M。

制作标记：A 级动作，矿道空间需控制镜头数量。

---

## 场 09 内景，矿道塌方后

鸢在塌方边缘找到陶罐碎片。

碎片内壁有黑红药痕，遇到空气后微微发热。

鸢用布包住，指尖还是被烫到。

凛藏抓住她手腕。

她的皮肤没有发黑，只是血管短暂浮出淡色纹路。

凛藏：你碰过这种东西。

鸢抽回手。

鸢：活下来，不等于懂它。

矿道外传来乌鸦声。

凛藏最后看了一眼塌方。铁链声已经停了。

尺度标记：M。

---

## 场 10 外景，沼泽村外围，黄昏

沼泽村没有狗叫。

也没有炊烟。

村口木牌写着“黑热”。牌子下堆着草鞋、破碗和小孩用的竹蜻蜓。

凛藏：绕过去。

鸢已经跨过封锁绳。

凛藏：你想死？

鸢：如果这里还有活人，绕过去的人也会死。

凛藏没有跟上。

鸢回头。

鸢：交易还没到讲义气的时候。你可以等。

她继续往里走。

凛藏站了一息，跟上。

尺度标记：C 预警。

---

## 场 11 内景/外景，沼泽村

村屋里全是潮气。

墙上药符被黑水泡烂。榻榻米下有轻微蠕动。

鸢掀开草席。

一个女孩缩在那里，八九岁，抱着破布娃娃。额头发黑，呼吸热得像炉口。

鸢把手背贴到女孩颈侧。

女孩没有醒。

门外泥水动了。

蛭丸从尸堆下站起来。

它瘦长，背后湿布包蠕动。腹部黑热斑纹一开一合，像另一张嘴在呼吸。

蛭丸：留下她。

鸢把女孩抱到身后。

凛藏站到门口。

蛭丸割开自己的手臂。

伤口里先涌出的不是血，而是一条条湿亮的蛭。

凛藏砍断第一批蛭。刀刃发黑。

鸢把药粉拍在刀上。

凛藏再次出刀。

门板被蛭群爬满。鸢点燃药烟，白烟贴着地面滚过，蛭群缩回泥水。

蛭丸吸食尸堆残血，伤口重新愈合。

凛藏看明白了。

他不再砍蛭丸身体，而是斩断它通向尸堆的路。鸢把盐药撒进泥水，蛭丸脚下冒白泡。

凛藏三步近身。

短刀刺入蛭丸喉下。

蛭丸抓住凛藏左腕。

凛藏旧封印烧痕发热，黑色血线沿皮肤浮起。

蛭丸怔了一下，像闻到什么。

凛藏没有给它说话的机会。

短刀横拉。

蛭丸倒进泥水，身体还在再生。

鸢把最后一包药粉塞进它伤口。

再生停止。

尺度标记：V2、M。

制作标记：寄生蛭以局部和反应表现，避免满屏虫群。

---

## 场 12 内景，村屋，夜

女孩被放在干草上。

鸢没有说话。

她把药碗放在膝前，割开指尖。

第一滴血落入碗中。

黑色药水变清了一瞬。

女孩睁开眼。

她看见鸢。

女孩很轻地动了动嘴。

没有声音。

鸢把药碗靠近她唇边。

女孩吞下一口。

额头黑斑退下去一点。

鸢的手还没放松，黑斑又爬回来。

她再割深一点。

凛藏伸手，按住她的手腕。

鸢没有看他，只盯着碗。

碗里的清色被黑慢慢吃掉。

女孩手里的破布娃娃滑落。

鸢停住。

屋外开始下细雨。

凛藏松开手。

鸢把药碗放下，替女孩合上眼。

她的指尖还在滴血。

没有人说话。

尺度标记：C、V3、M。

导演备注：不得表现儿童痛苦过程，情绪由药水变化、鸢的手和沉默承担。

---

## 场 13 外景，沼泽村夜

鸢把女孩埋在村口，没有立木牌。

凛藏站在远处。

雨把泥土压平。

鸢：你说这里是试验场。

凛藏：我见过一样的死法。

鸢：感染村。

凛藏没有回答。

鸢：你不是唯一一个被那件事留下来的人。

凛藏看向她。

鸢：我救不了她。但我知道是谁让她变成这样。

凛藏：知道名字，不等于能杀。

鸢：那就先把路找出来。

这一次，凛藏没有走在她后面。

他和她并肩离开村口。

尺度标记：C 后果。

---

## 场 14 外景，荒寺外，黎明

荒寺在雾里。

寺门半塌，门前挤着灾民和流浪艺人。有人烧水，有人包扎伤口，有人用破布盖住脸上的黑斑。

远处传来琵琶声。

每拨一下，灾民们的动作就慢一分。

凛藏脚下石阶像向左倾斜。

鸢捂住耳朵。

鸢：声音有问题。

凛藏把短刀丢到地上。

刀在石阶上滚了半圈，停住。

凛藏看着刀停下的位置，重新校正脚步。

凛藏：走直线。

琵琶声再次响起。

荒寺深处，有人笑了一声。

尺度标记：M 预警。

制作标记：进入骨琵琶段，声音设计优先。

## 返修完成项

1. 废矿战已压缩，保留核心视觉和剧情信息。
2. 蛭丸不再直接解释旧药，通过凛藏腕部反应暗示。
3. 千代死亡段减少对白，使用药水和动作表达。
4. 荒寺钩子改为“用刀落点校正空间”，更硬、更可分镜。
5. 每场已补尺度标记。
"""


def build_storyboard_director_review(task: dict) -> str:
    source = DATA_DIR / "outputs" / "TASK-008_storyboard_breakdown.md"
    source_note = source.name
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    shot_count = sum(1 for line in text.splitlines() if line.startswith("| ") and "-" in line.split("|")[1])
    s_shot_count = 5 if "S-shot 暂定 5 个" in text else 0
    source_status = "found" if source.exists() else "missing"
    return f"""# DirectorAgent Storyboard Review: 第二幕上 v0.2 分镜拆解

审查对象：{source_note}（source {source_status}）

任务：{task.get("title", "")}

结论：Conditional approve for thumbnail pass。可进入缩略分镜制作，但 6 个镜头需要在画面草图前修正。

## 总体判断

StoryboardAgent 已经把第二幕上半拆成 {shot_count} 镜，并把 RiskAgent 的国际版条件带进镜头表。分镜方向正确：废矿战没有扩成样片级大段，蛭丸段用局部、反应和声音控制寄生数量，千代死亡段转向药碗、布娃娃、手部表演和静默，荒寺入口以声音和空间错位进入下一段。

暂定 S-shot 数量：{s_shot_count}。这个数量适合进入缩略分镜阶段，但后续 ProducerAgent 必须按 S-shot 成本复核。

## 可直接进入缩略分镜的镜头

07-001、07-002、07-004、08-001、08-002、08-005、08-006、08-007、08-008、09-001、09-002、10-001、10-002、11-001、11-002、11-005、12-001、12-002、12-003、13-001、13-002、14-001、14-002、14-003、14-004。

## 画面草图前必须修正

1. 07-003：眼形暗记要更抽象，不能形成任何可被误读为既有作品或真实组织标志的符号。
2. 08-003：矿工尸体局部镜头只保留信息功能，缩略图中不要出现可识别痛苦表情。
3. 08-004：铁蜈蚣顶壁落下是 S-shot，但要先定剪影，不要先堆细节。
4. 08-009：影目付烧印只给一息，不能成为反复出现的视觉商标。
5. 11-003：蛭丸从尸堆起身要先出“泥水形状”，再出人形，降低尸堆猎奇感。
6. 11-004：寄生蛭数量上限写进分镜备注，国际版默认用反应镜头和声音替换。

## 千代段导演要求

12-001 到 12-003 是本段情绪核心，但不设 S-shot。缩略图必须严格执行 RiskAgent 条件：不画儿童痛苦过程，不画死亡瞬间特写，以药水颜色、布娃娃、鸢手部动作、凛藏站位和雨声完成情绪。

## 下游派工

1. StoryboardAgent：按以上 6 条修正生成 v0.2 分镜表。
2. VisualDesignAgent：先做 07-003 眼形暗记、08-004 铁蜈蚣剪影、11-003 蛭丸泥水剪影、14-002 空间扭曲四项视觉草案。
3. ActionAgent：只拆 08-004 到 08-008 与 11-003 到 11-005，不扩写 12 段。
4. CompAgent：优先测试白火、泥水反应、药碗变色、琵琶空间错位。
5. RiskAgent：复核 08-003、11-004、12-001 到 12-003 的缩略图。
6. ProducerAgent：以 31 镜、5 个 S-shot 为基准估算分镜/动作/合成试制工时。

## 建议审查状态

Return to StoryboardAgent for v0.2 corrections, then approve thumbnails if the six required fixes are present.
"""


def build_director_review(task: dict) -> str:
    task_text = f"{task.get('title', '')} {task.get('prompt', '')}"
    if (
        "TASK-008" in task_text
        or "storyboard" in task_text.lower()
        or "thumbnail" in task_text.lower()
        or "分镜" in task_text
    ):
        return build_storyboard_director_review(task)

    task_text = f"{task.get('title', '')} {task.get('prompt', '')}"
    is_second_review = "TASK-005" in task_text or "v0.2" in task_text or "second" in task_text.lower()
    source = DATA_DIR / "outputs" / (
        "TASK-005_writer_revision_v02.md" if is_second_review else "TASK-001_writer_output.md"
    )
    source_note = source.name
    text = ""
    if source.exists():
        text = source.read_text(encoding="utf-8")
    word_count = len(text)
    has_mine = "废矿" in text and "铁蜈蚣" in text
    has_swamp = "沼泽" in text and "蛭丸" in text
    has_chiyo = "千代" in text
    has_rating = "V3" in text or "C：" in text or "C:" in text
    verdict = "Return with notes"
    if has_mine and has_swamp and has_chiyo and has_rating:
        verdict = "Approve as director-discussion draft" if is_second_review else "Conditional approve for writer-room discussion"

    if is_second_review:
        return f"""# DirectorAgent Second Review: 第二幕上 v0.2

审查对象：{source_note}

任务：{task.get("title", "")}

结论：{verdict}

## 总体判断

v0.2 已基本执行上一轮导演意见。废矿铁蜈蚣战被压缩为更清晰的环境战，蛭丸不再重复解释旧药/药炉，千代死亡段转为药水变化、鸢手部动作和沉默承载情绪，荒寺钩子也从文学化台词改成“用刀落点校正空间”的可分镜动作。

草稿长度约 {word_count} 字符。它可以进入导演/编剧讨论会，作为第二幕上半的“导演可讨论版”。

## 已满足的返修项

1. 废矿战压缩有效：矿灯、白火、塌方、影目付烧印四个核心点保留。
2. 旧药信息不再靠敌人说明，改为凛藏腕部反应和蛭丸嗅觉停顿。
3. 千代死亡段对白明显减少，风险处理更克制。
4. 荒寺钩子更硬，能直接转成分镜动作。
5. 每场补了尺度标记，便于 RiskAgent 后续审查。

## 仍需导演稿处理

1. “影目付烧印”在铁蜈蚣处保留，但后续敌人不要再频繁出现同类标记。
2. 鸢和凛藏在沼泽村后并肩离开的动作有效，导演稿可再压一句对白。
3. 荒寺段进入骨琵琶前，需要给灾民状态一个更短但更刺眼的视觉细节。
4. 场 11 的寄生蛭视觉必须限制数量，优先用泥水、局部和声音表达。

## 制片判断

通过进入下一阶段：第二幕上半可进入编剧室讨论和动作/美术拆解。暂不锁定为最终导演稿。

建议状态：Approved for director discussion.
"""

    return f"""# DirectorAgent Review: 第二幕上 WriterAgent 草稿

审查对象：{source_note}

任务：{task.get("title", "")}

结论：{verdict}

## 总体判断

这版草稿已经完成第二幕上半的基本功能：从第一幕“这是旧账”自然推进到废矿、铁蜈蚣、沼泽村、蛭丸和千代之死，并让鸢的行动动机从“护送密信”变成“她确实要救眼前的人”。凛藏在沼泽村后第一次真正看见鸢，这个关系变化是有效的。

草稿长度约 {word_count} 字符，适合作为编剧室讨论稿，不应直接锁为导演稿。

## 通过项

1. 废矿段有明确空间规则：狭窄矿道限制长刀，迫使凛藏换短刀和环境战术。
2. 铁蜈蚣的能力与场景绑定，链刃、顶壁爬行、矿道塌方都能转为分镜动作。
3. 鸢不是旁观者，她用矿物判断、射落矿灯、撒药粉、救千代，行动力成立。
4. 沼泽村把黑热从阴谋设定变成具体伤害，千代死亡承担了情感功能。
5. 蛭丸战斗有可读规则：尸堆供血、寄生蛭、盐药限制再生。
6. 结尾荒寺琵琶声作为下一段钩子有效。

## 需要修改

1. 铁蜈蚣死亡前出现影目付烧印很好，但需要更克制，不要让每个敌人都直接说出主角身份，否则信息重复。
2. 鸢“你说过，普通刀伤未必有用”略像引用第一幕台词，可改得更自然。
3. 蛭丸说“你也是炉里出来的”信息有效，但和水母尼的旧药台词功能接近，建议压短或换成身体反应。
4. 千代死亡段落方向正确，但需要减少“解释”，更多依赖鸢手上动作、药水变清又变黑、凛藏站在门边的沉默。
5. 场 14 荒寺入口很好，但“信刀落地的声音”略漂亮，可能偏文学化。导演稿可改得更硬。

## 制作提醒

1. 废矿段应控制镜头数量，不要把铁蜈蚣战扩成第二个样片级大段。
2. 沼泽村寄生蛭数量必须可控，建议以近景、反应、泥水动静表现，不做满屏虫群。
3. 千代死亡属于 C/V3 风险，必须保持克制，不能用痛苦过程换情绪。
4. 荒寺段进入前应留一口气，不要让第二幕上半连续三场动作过密。

## 给 WriterAgent 的返修指令

1. 压缩废矿战 15%，保留矿灯、白火、塌方和烧印四个关键点。
2. 改写蛭丸台词，减少解释“旧药/药炉”重复。
3. 重写千代死亡段，让鸢少说话，动作多一点。
4. 保留荒寺钩子，但降低台词文学感。
5. 在每场末尾补充尺度标记：V2、V3、C、M。

## 建议审查状态

Needs revision, but suitable for writer-room development.
"""


def build_risk_review(task: dict) -> str:
    source = DATA_DIR / "outputs" / "TASK-005_writer_revision_v02.md"
    source_note = source.name
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    marker_counts = {
        "V2": text.count("V2"),
        "V3": text.count("V3"),
        "C": text.count("C"),
        "M": text.count("M"),
    }
    source_status = "found" if source.exists() else "missing"
    return f"""# RiskAgent Review: 第二幕上 v0.2 尺度与发行风险

审查对象：{source_note}（source {source_status}）

任务：{task.get("title", "")}

结论：Conditional pass。可进入分镜前讨论，但高风险场次必须保留国际版替代方案。

## 自动标记扫描

- V2 标记：{marker_counts["V2"]}
- V3 标记：{marker_counts["V3"]}
- C 标记：{marker_counts["C"]}
- M 标记：{marker_counts["M"]}

## 主要风险判断

1. 场 08 废矿铁蜈蚣：V2/M。成人动作片尺度可控，但铁节、人体改造和矿工尸体镜头不宜连续近景堆叠。国际版可减少尸体背部切分特写，以矿灯、拖拽声和凛藏反应替代。
2. 场 11 沼泽蛭丸：V2/M。寄生、体温、旧药反应容易进入 body horror 区域。分镜阶段应优先使用泥水波纹、腕部反应、村民停顿和声音设计，避免满屏虫群。
3. 场 12 千代死亡：C/V3/M。全段最高风险。不得表现儿童痛苦过程，不使用痛苦特写换情绪。建议以药碗、布娃娃、鸢的手部动作、凛藏站位和静默完成表达。
4. 场 14 荒寺入口：M 预警。骨琵琶与空间错位可保留，但不要出现可模仿的自残细节或过度解释性台词。

## 原创性与参考风险

项目可继续保持“成人忍者动作、怪异敌人、冷硬江户末世感”的高层类型方向，但分镜和角色造型必须避开任何既有作品的标志性构图、武器动作、敌人组合和死亡设计。建议在视觉开发阶段使用内部关键词表，而不是把单一经典作品作为逐镜参考。

## 分镜阶段强制要求

1. 每个 V3/C 场次必须提供 domestic cut 与 international cut 两版镜头策略。
2. 铁蜈蚣和蛭丸段要限制 S-shot 数量，避免风险与预算同时外溢。
3. 千代死亡段以反应镜头和道具变化为主，不做痛苦过程动画。
4. 宣传文案不得使用“复刻”“致敬某片”等表达，只能使用类型描述和原创卖点。
5. DirectorAgent 分镜审查前，RiskAgent 需要复核分镜缩略图。

## 建议审查状态

Approved with conditions for storyboard development.
"""


def build_storyboard_breakdown(task: dict) -> str:
    script_source = DATA_DIR / "outputs" / "TASK-005_writer_revision_v02.md"
    director_source = DATA_DIR / "outputs" / "TASK-006_director_review.md"
    risk_source = DATA_DIR / "outputs" / "TASK-007_risk_review.md"
    script_status = "found" if script_source.exists() else "missing"
    director_status = "found" if director_source.exists() else "missing"
    risk_status = "found" if risk_source.exists() else "missing"
    shots = [
        ["07-001", "废矿入口", "LS / slow push", "雨后山雾、车辙、黑色矿粉引出废矿", "BG mist, wet ground, mineral glint", "M", "保留"],
        ["07-002", "废矿入口", "CU / static", "银针挑起矿粉，针尖发热", "prop: silver needle, heat shimmer", "M", "保留"],
        ["07-003", "废矿入口", "MS / rack focus", "旧封条、幕府官印、眼形暗记", "graphic mark must be original", "Originality", "保留但避免既有标志感"],
        ["07-004", "废矿入口", "OTS / hold", "金属拖地声从矿道深处传来，凛藏换短刀", "sound lead-in", "M", "保留"],
        ["08-001", "废矿深处", "WS / narrow frame", "矿道窄，长刀无法展开", "tight BG layout", "Budget", "保留"],
        ["08-002", "废矿深处", "CU / pan", "爬行抓痕指向更深处", "wall scratches, dust", "M", "保留"],
        ["08-003", "废矿深处", "MCU / cutaway", "矿工尸体倒挂，背部切分只给局部", "partial corpse only", "V2/M", "国际版减少停留"],
        ["08-004", "废矿深处", "Low angle / snap tilt", "铁蜈蚣从顶壁落下", "chain blade rig, dust fall", "V2/M", "保留"],
        ["08-005", "废矿深处", "MS / lateral track", "短刀切腕被铁箍挡住", "sparks, metal hit", "V2", "保留"],
        ["08-006", "废矿深处", "CU / fast insert", "鸢射断矿灯吊绳", "falling lamp", "Budget", "保留"],
        ["08-007", "废矿深处", "WS / flash frame", "白火照出腐朽横梁", "white fire comp, silhouette", "V2/M", "保留"],
        ["08-008", "废矿深处", "WS / shake", "支架塌落压住铁蜈蚣", "debris pass, dust layer", "V2", "国际版缩短压迫过程"],
        ["08-009", "废矿深处", "CU / short hold", "手腕旧影目付烧印，凛藏停一息", "brand design original", "Originality", "保留"],
        ["09-001", "塌方边缘", "CU / static", "陶罐碎片黑红药痕发热", "prop FX", "M", "保留"],
        ["09-002", "塌方边缘", "MCU / hold", "鸢血管淡色纹路浮现又退去", "subtle vein FX", "M", "保留"],
        ["10-001", "沼泽村口", "LS / static", "无狗叫、无炊烟，黑热门牌和草鞋破碗", "quiet BG, prop scatter", "C warning", "保留"],
        ["10-002", "沼泽村口", "Two-shot / split depth", "鸢越过封锁绳，凛藏犹豫后跟上", "character blocking", "C warning", "保留"],
        ["11-001", "村屋", "CU / creep", "榻榻米下轻微蠕动", "sound + tiny motion only", "V2/M", "国际版可用声音替代画面"],
        ["11-002", "村屋", "MS / reveal", "千代抱布娃娃，额头黑热", "child design restrained", "C/M", "不得表现痛苦过程"],
        ["11-003", "村外泥水", "Low WS / ripple", "泥水动，蛭丸从尸堆下站起", "mud ripple, silhouette first", "V2/M", "国际版减少尸堆细节"],
        ["11-004", "村屋门口", "MS / impact cuts", "蛭丸割臂，寄生蛭只给局部和反应", "parasite count capped", "V2/M", "国际版用反应和声音"],
        ["11-005", "村屋门口", "Action WS / three beats", "凛藏断退路，鸢撒盐药，蛭丸再生停止", "mud foam, smoke layer", "V2", "保留"],
        ["12-001", "村屋夜", "CU / static", "药水短暂变清，又泛黑", "medicine bowl color shift", "C/V3/M", "核心替代镜头"],
        ["12-002", "村屋夜", "CU / hand", "鸢握住布娃娃，手停住", "hand acting", "C/V3/M", "国内外版一致"],
        ["12-003", "村屋夜", "MS / doorway hold", "凛藏站在门边，不说话", "silence, rain bed", "C/V3/M", "禁止儿童痛苦特写"],
        ["13-001", "沼泽村夜", "LS / static", "村口无名小坟，雨再次落下", "rain, low contrast", "C", "保留"],
        ["13-002", "沼泽村夜", "Two-shot / slow pan", "鸢与凛藏关系转折，并肩离开", "performance shot", "M", "保留"],
        ["14-001", "荒寺外黎明", "LS / fog reveal", "灾民与流浪艺人聚在半塌寺门", "crowd economical loops", "M", "保留"],
        ["14-002", "荒寺石阶", "POV / subtle skew", "琵琶声使石阶倾斜", "comp warp, sound cue", "M", "保留"],
        ["14-003", "荒寺石阶", "CU / drop", "凛藏丢短刀，用落点校正空间", "prop animation, sound sync", "M", "保留"],
        ["14-004", "荒寺深处", "Black hold / sound", "荒寺深处笑声，进入骨琵琶段", "sound-first transition", "M", "保留"],
    ]
    rows = "\n".join(
        f"| {shot_id} | {scene} | {camera} | {action} | {fx} | {risk} | {cut} |"
        for shot_id, scene, camera, action, fx, risk, cut in shots
    )
    return f"""# StoryboardAgent Output: 第二幕上 v0.2 分镜拆解

任务：{task.get("title", "")}

输入状态：

- 剧本稿：{script_source.name}（{script_status}）
- 导演二审：{director_source.name}（{director_status}）
- 风险审查：{risk_source.name}（{risk_status}）

## 分镜目标

把第二幕上半从编剧讨论稿推进为可进入缩略分镜的镜头清单。镜头设计遵守 DirectorAgent 的节奏要求：废矿战压缩、蛭丸段控制寄生数量、千代死亡克制、荒寺入口留气口。也遵守 RiskAgent 条件：V3/C 场次必须有国际版替代策略，分镜阶段不得借用既有作品标志性构图。

## 镜头表 v0.1

| 镜号 | 场次 | 景别/运动 | 画面动作 | 美术/FX/声音提示 | 风险 | 国际版策略 |
|---|---|---|---|---|---|---|
{rows}

## 节奏与产能判断

- 合计 31 镜。废矿 13 镜，沼泽村与千代段 12 镜，荒寺入口 4 镜，过场 2 镜。
- S-shot 暂定 5 个：08-004、08-007、08-008、11-003、14-002。
- 千代死亡段不设 S-shot，用表演、道具和静默完成情绪，避免风险和预算双重外溢。
- 蛭丸寄生效果只做局部运动库，不做满屏群体模拟。

## 给下游 Agent 的任务

1. VisualDesignAgent：输出铁蜈蚣、蛭丸、骨琵琶入口、黑热药痕四组原创视觉关键词。
2. ActionAgent：拆 08-004 到 08-008、11-003 到 11-005 的动作三拍，保证刀路清晰。
3. CompAgent：测试白火、泥水、药碗变色、琵琶空间扭曲四个效果。
4. RiskAgent：复核 08-003、11-004、12-001 到 12-003 的缩略分镜。
5. ProducerAgent：按 31 镜、5 个 S-shot 估算样段或正片单集段落成本。

## 建议审查状态

Needs DirectorAgent storyboard review before locking thumbnails.
"""


def build_storyboard_revision(task: dict) -> str:
    previous_source = DATA_DIR / "outputs" / "TASK-008_storyboard_breakdown.md"
    director_source = DATA_DIR / "outputs" / "TASK-009_director_review.md"
    risk_source = DATA_DIR / "outputs" / "TASK-007_risk_review.md"
    previous_status = "found" if previous_source.exists() else "missing"
    director_status = "found" if director_source.exists() else "missing"
    risk_status = "found" if risk_source.exists() else "missing"
    shots = [
        ["07-001", "废矿入口", "LS / slow push", "雨后山雾、车辙、黑色矿粉引出废矿", "BG mist, wet ground, mineral glint", "M", "保留", ""],
        ["07-002", "废矿入口", "CU / static", "银针挑起矿粉，针尖发热", "prop: silver needle, heat shimmer", "M", "保留", ""],
        ["07-003", "废矿入口", "CU / rack focus", "旧封条下只露一段不完整刻痕，像被雨水冲散的半圈裂纹", "abstract broken mark; no eye icon; no emblem symmetry", "Originality", "保留但不得作为标志特写", "修正：眼形暗记改成抽象裂纹，取消可识别眼形符号"],
        ["07-004", "废矿入口", "OTS / hold", "金属拖地声从矿道深处传来，凛藏换短刀", "sound lead-in", "M", "保留", ""],
        ["08-001", "废矿深处", "WS / narrow frame", "矿道窄，长刀无法展开", "tight BG layout", "Budget", "保留", ""],
        ["08-002", "废矿深处", "CU / pan", "爬行抓痕指向更深处", "wall scratches, dust", "M", "保留", ""],
        ["08-003", "废矿深处", "Insert / one-second cutaway", "只给矿工衣料、木架阴影和背部切分轮廓，不出现脸", "partial corpse silhouette; no pain expression", "V2/M", "国际版可删本镜，以拖拽声替代", "修正：取消可识别痛苦表情，镜头只承担信息功能"],
        ["08-004", "废矿深处", "Low silhouette / snap tilt", "铁蜈蚣先以顶壁剪影落下，第二拍才露链刃轮廓", "silhouette-first S-shot; detail pass later", "V2/M", "保留", "修正：先定剪影，不先堆细节"],
        ["08-005", "废矿深处", "MS / lateral track", "短刀切腕被铁箍挡住", "sparks, metal hit", "V2", "保留", ""],
        ["08-006", "废矿深处", "CU / fast insert", "鸢射断矿灯吊绳", "falling lamp", "Budget", "保留", ""],
        ["08-007", "废矿深处", "WS / flash frame", "白火照出腐朽横梁", "white fire comp, silhouette", "V2/M", "保留", ""],
        ["08-008", "废矿深处", "WS / shake", "支架塌落压住铁蜈蚣", "debris pass, dust layer", "V2", "国际版缩短压迫过程", ""],
        ["08-009", "废矿深处", "Insert / half-second hold", "手腕旧烧印只掠过一瞬，凛藏视线停住", "brand not repeated; abstract scar geometry", "Originality", "保留但不得成为反复商标", "修正：烧印压到一息内，只服务凛藏反应"],
        ["09-001", "塌方边缘", "CU / static", "陶罐碎片黑红药痕发热", "prop FX", "M", "保留", ""],
        ["09-002", "塌方边缘", "MCU / hold", "鸢血管淡色纹路浮现又退去", "subtle vein FX", "M", "保留", ""],
        ["10-001", "沼泽村口", "LS / static", "无狗叫、无炊烟，黑热门牌和草鞋破碗", "quiet BG, prop scatter", "C warning", "保留", ""],
        ["10-002", "沼泽村口", "Two-shot / split depth", "鸢越过封锁绳，凛藏犹豫后跟上", "character blocking", "C warning", "保留", ""],
        ["11-001", "村屋", "CU / creep", "榻榻米下轻微蠕动", "sound + tiny motion only", "V2/M", "国际版可用声音替代画面", ""],
        ["11-002", "村屋", "MS / reveal", "千代抱布娃娃，额头黑热", "child design restrained", "C/M", "不得表现痛苦过程", ""],
        ["11-003", "村外泥水", "Low WS / staged reveal", "泥水先鼓起成人形空洞，蛭丸轮廓随后从水面立起", "mud shape first; corpse pile out of focus", "V2/M", "国际版只保留泥水人形和反应", "修正：先出泥水形状，降低尸堆猎奇感"],
        ["11-004", "村屋门口", "Reaction-led inserts", "蛭丸割臂不正面展示，寄生蛭上限 8 条，以鸢和凛藏反应承接", "parasite cap: 8; sound replaceable", "V2/M", "默认用反应镜头和声音替换", "修正：写入寄生数量上限和国际版默认替换"],
        ["11-005", "村屋门口", "Action WS / three beats", "凛藏断退路，鸢撒盐药，蛭丸再生停止", "mud foam, smoke layer", "V2", "保留", ""],
        ["12-001", "村屋夜", "CU / static", "药水短暂变清，又泛黑", "medicine bowl color shift", "C/V3/M", "核心替代镜头", ""],
        ["12-002", "村屋夜", "CU / hand", "鸢握住布娃娃，手停住", "hand acting", "C/V3/M", "国内外版一致", ""],
        ["12-003", "村屋夜", "MS / doorway hold", "凛藏站在门边，不说话", "silence, rain bed", "C/V3/M", "禁止儿童痛苦特写", ""],
        ["13-001", "沼泽村夜", "LS / static", "村口无名小坟，雨再次落下", "rain, low contrast", "C", "保留", ""],
        ["13-002", "沼泽村夜", "Two-shot / slow pan", "鸢与凛藏关系转折，并肩离开", "performance shot", "M", "保留", ""],
        ["14-001", "荒寺外黎明", "LS / fog reveal", "灾民与流浪艺人聚在半塌寺门", "crowd economical loops", "M", "保留", ""],
        ["14-002", "荒寺石阶", "POV / subtle skew", "琵琶声使石阶倾斜", "comp warp, sound cue", "M", "保留", ""],
        ["14-003", "荒寺石阶", "CU / drop", "凛藏丢短刀，用落点校正空间", "prop animation, sound sync", "M", "保留", ""],
        ["14-004", "荒寺深处", "Black hold / sound", "荒寺深处笑声，进入骨琵琶段", "sound-first transition", "M", "保留", ""],
    ]
    rows = "\n".join(
        f"| {shot_id} | {scene} | {camera} | {action} | {fx} | {risk} | {cut} | {note or '-'} |"
        for shot_id, scene, camera, action, fx, risk, cut, note in shots
    )
    return f"""# StoryboardAgent Output: 第二幕上 v0.2 分镜拆解返修稿

任务：{task.get("title", "")}

输入状态：

- 上版分镜：{previous_source.name}（{previous_status}）
- 导演分镜审查：{director_source.name}（{director_status}）
- 风险审查：{risk_source.name}（{risk_status}）

## 返修目标

执行 DirectorAgent 对 6 个镜头的退回意见：07-003、08-003、08-004、08-009、11-003、11-004。返修重点是原创符号安全、尸体/寄生尺度控制、S-shot 先定剪影、以及国际版默认替代方案。

## 镜头表 v0.2

| 镜号 | 场次 | 景别/运动 | 画面动作 | 美术/FX/声音提示 | 风险 | 国际版策略 | 返修备注 |
|---|---|---|---|---|---|---|---|
{rows}

## 返修完成项

1. 07-003 取消眼形暗记，改为抽象裂纹，避免符号近似和商标化。
2. 08-003 去除可识别脸部与痛苦表情，国际版可删镜。
3. 08-004 铁蜈蚣先做剪影 S-shot，细节后置到设计 Agent。
4. 08-009 烧印压缩为半秒信息点，不反复作为视觉标志。
5. 11-003 蛭丸先以泥水人形出现，尸堆退到失焦背景。
6. 11-004 寄生蛭数量上限设为 8，国际版默认反应/声音替换。

## 下游派工更新

1. DirectorAgent：复审 v0.2 六个修正镜头，若通过则批准缩略分镜。
2. VisualDesignAgent：只先做抽象裂纹、铁蜈蚣剪影、蛭丸泥水人形、琵琶空间扭曲。
3. RiskAgent：优先复核 08-003、11-004、12-001 到 12-003。
4. ProducerAgent：仍按 31 镜、5 个 S-shot 估算，但 08-004 细节设计暂不进入动画成本。

## 建议审查状态

Ready for DirectorAgent v0.2 storyboard review.
"""


def simulate_agent_output(task: dict) -> str:
    agent = task.get("agent", "Agent")
    title = task.get("title", "Untitled task")
    prompt = task.get("prompt", "")
    task_text = f"{title} {prompt}"
    if agent in {"DirectorAgent", "RiskAgent"} and any(
        marker in task_text.lower()
        for marker in ["product sample", "act2_01_sample", "limited animation", "final sample"]
    ):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "sample_production_agent.py"),
                "--stage",
                "review",
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest["report"]
        return f"{agent} generated product sample review report: {manifest['report']}"
    if agent == "WriterAgent":
        wants_revision = any(
            marker in f"{title} {prompt}".lower()
            for marker in ["revision", "v0.2", "revise", "returned"]
        ) or any(marker in f"{title} {prompt}" for marker in ["返修", "退回", "修改"])
        draft = build_act_two_upper_revision(task) if wants_revision else build_act_two_upper_draft(task)
        suffix = "writer_revision_v02" if wants_revision else "writer_output"
        output_path = write_named_output_markdown(task["id"], suffix, draft)
        task["output_file"] = output_path
        label = "revision draft" if wants_revision else "reviewable Act II upper draft"
        return f"WriterAgent generated a {label}: {output_path}"
    if agent == "DirectorAgent":
        review = build_director_review(task)
        output_path = write_named_output_markdown(task["id"], "director_review", review)
        task["output_file"] = output_path
        return f"DirectorAgent generated review notes: {output_path}"
    if agent == "ProducerAgent":
        return (
            f"Production note for {title}: check scope, S-shot count, 8-week sample schedule, "
            "and budget variance before approval."
        )
    if agent == "RiskAgent":
        review = build_risk_review(task)
        output_path = write_named_output_markdown(task["id"], "risk_review", review)
        task["output_file"] = output_path
        return f"RiskAgent generated risk review notes: {output_path}"
    if agent == "StoryboardAgent":
        wants_revision = any(
            marker in f"{title} {prompt}".lower()
            for marker in ["revision", "v0.2", "revise", "returned"]
        ) or any(marker in f"{title} {prompt}" for marker in ["返修", "退回", "修正", "TASK-009"])
        breakdown = build_storyboard_revision(task) if wants_revision else build_storyboard_breakdown(task)
        suffix = "storyboard_breakdown_v02" if wants_revision else "storyboard_breakdown"
        output_path = write_named_output_markdown(task["id"], suffix, breakdown)
        task["output_file"] = output_path
        label = "storyboard revision" if wants_revision else "storyboard breakdown"
        return f"StoryboardAgent generated {label}: {output_path}"
    if agent == "AnimaticAgent":
        manifest_path = ANIME_PROJECT / "media" / "act2_storyboard_v02" / "manifest.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "animatic_agent.py"), "--task-id", task["id"], "--quiet"],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        task["output_file"] = manifest["video"]
        task["manifest_file"] = result.stdout.strip() or str(manifest_path.relative_to(WORKSPACE))
        return (
            f"AnimaticAgent rendered {manifest['shot_count']} storyboard boards and "
            f"{manifest['duration_seconds']}s MP4 animatic: {manifest['video']}"
        )
    if agent in {"VisualDesignAgent", "AnimationAgent", "AudioAgent", "EditAgent"}:
        stage_by_agent = {
            "VisualDesignAgent": "visual",
            "AnimationAgent": "animation",
            "AudioAgent": "audio",
            "EditAgent": "edit",
        }
        stage = stage_by_agent[agent]
        is_master_edit = agent == "EditAgent" and any(
            marker in task_text.lower() for marker in ["master", "preview", "concat", "multiple", "多段", "总剪辑"]
        )
        is_onsen = not is_master_edit and any(marker in task_text.lower() for marker in ["onsen", "温泉", "rainy"])
        if is_master_edit:
            result = subprocess.run(
                [sys.executable, str(ROOT / "master_edit_agent.py"), "--task-id", task["id"], "--quiet"],
                check=True,
                cwd=str(WORKSPACE),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            manifest_file = result.stdout.strip()
        else:
            script = "onsen_segment_agent.py" if is_onsen else "sample_production_agent.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / script),
                    "--stage",
                    stage,
                    "--task-id",
                    task["id"],
                    "--quiet",
                ],
                check=True,
                cwd=str(WORKSPACE),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        if agent == "EditAgent":
            task["output_file"] = manifest["video"]
            return f"EditAgent rendered final MP4: {manifest['video']}"
        if agent == "AudioAgent":
            task["output_file"] = manifest["audio"]
            return f"AudioAgent generated temp audio track: {manifest['audio']}"
        if agent == "AnimationAgent":
            task["output_file"] = manifest_file
            return f"AnimationAgent rendered {manifest['shot_count']} shot MP4 files: {manifest_file}"
        task["output_file"] = manifest_file
        return f"VisualDesignAgent generated {manifest['asset_count']} layered visual assets: {manifest_file}"
    if agent == "ToolRouterAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipeline_tool_router.py"),
                "--target",
                "master_preview",
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ToolRouterAgent generated external provider job packets for "
            f"{manifest['shot_count']} shots: {manifest_file}"
        )
    if agent == "ProviderAdapterAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "provider_adapter_agent.py"),
                "--provider",
                "all",
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ProviderAdapterAgent generated {manifest['total_request_packets']} dry-run provider "
            f"request packets across {len(manifest['providers'])} providers: {manifest_file}"
        )
    if agent == "CodeVideoAdapterAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "code_video_adapter_agent.py"),
                "--selected-only",
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"CodeVideoAdapterAgent rendered {manifest['rendered_count']} Remotion-style "
            f"MP4 files into the external inbox: {manifest_file}"
        )
    if agent == "ExternalVideoProviderAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_video_provider_agent.py"),
                "--provider",
                "all",
                "--selected-only",
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ExternalVideoProviderAgent prepared {manifest['total_submission_count']} submit-ready chunks "
            f"for {manifest['provider_count']} video providers; "
            f"{manifest['ready_provider_count']} configured for API submit: {manifest_file}"
        )
    if agent == "ExternalChunkAssemblyAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_chunk_assembly_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ExternalChunkAssemblyAgent assembled {manifest['assembled_count']} final MP4s; "
            f"{manifest['waiting_count']} shot groups still waiting for provider chunks: {manifest_file}"
        )
    if agent == "ExternalSubmitGateAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_submit_gate_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("approval_request", manifest_file)
        return (
            f"ExternalSubmitGateAgent evaluated {manifest['provider_count']} providers: "
            f"{manifest['allowed_provider_count']} allowed, {manifest['blocked_provider_count']} blocked, "
            f"estimated total cost ${manifest['total_estimated_cost_usd']}. Approval request: "
            f"{manifest['approval_request']}"
        )
    if agent == "ExternalProviderSubmitAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_provider_submit_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ExternalProviderSubmitAgent prepared submit run: {manifest['submitted_count']} submitted/prepared, "
            f"{manifest['blocked_provider_count']} providers blocked, {manifest['failed_count']} failed: {manifest_file}"
        )
    if agent == "ExternalProviderPollAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_provider_poll_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ExternalProviderPollAgent checked {manifest['submitted_item_count']} submitted items: "
            f"{manifest['ready_for_download_count']} ready, {manifest['pending_count']} pending, "
            f"{manifest['downloaded_count']} downloaded: {manifest_file}"
        )
    if agent == "ExternalResultReviewAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_result_review_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"ExternalResultReviewAgent reviewed {manifest['reviewed_count']} accepted results: "
            f"{manifest['approved_count']} approved, {manifest['returned_count']} returned. Report: "
            f"{manifest['report']}"
        )
    if agent == "ShotReplacementAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "shot_replacement_agent.py"),
                "--stage",
                "all",
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest["video"]
        return f"ShotReplacementAgent generated replacement master preview: {manifest['video']}"
    if agent == "MasterAcceptanceAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "master_acceptance_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"MasterAcceptanceAgent decision: {manifest['decision']}; "
            f"{manifest['checklist']['passed_count']} checks passed, "
            f"{manifest['checklist']['failed_count']} failed. Report: {manifest['report']}"
        )
    if agent == "DirectorRiskReviewAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "director_risk_review_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"DirectorRiskReviewAgent decision: {manifest['decision']}; "
            f"{manifest['nonblank_keyframe_count']}/{manifest['reviewed_keyframe_count']} keyframes nonblank. "
            f"Contact sheet: {manifest['contact_sheet']}"
        )
    if agent == "DirectorRiskReviewV2Agent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "director_risk_review_v02_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"DirectorRiskReviewV2Agent decision: {manifest['decision']}; "
            f"{manifest['nonblank_keyframe_count']}/{manifest['reviewed_keyframe_count']} keyframes nonblank. "
            f"Contact sheet: {manifest['contact_sheet']}"
        )
    if agent == "ProducerDemoPackageAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "producer_demo_package_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("zip", {}).get("path", manifest_file)
        return (
            f"ProducerDemoPackageAgent decision: {manifest['decision']}; "
            f"{manifest['artifact_count']} artifacts packaged. Zip: {manifest['zip']['path']}"
        )
    if agent == "ProducerDemoV2PackageAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "producer_demo_v02_package_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("zip", {}).get("path", manifest_file)
        return (
            f"ProducerDemoV2PackageAgent decision: {manifest['decision']}; "
            f"{manifest['artifact_count']} artifacts packaged. Zip: {manifest['zip']['path']}"
        )
    if agent == "CurrentDemoPromotionAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "current_demo_promotion_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("current_zip", manifest_file)
        return (
            f"CurrentDemoPromotionAgent promoted {manifest['current_version']} to current demo; "
            f"zip entries: {manifest['zip_entry_count']}. Current zip: {manifest['current_zip']}"
        )
    if agent == "HighQualityPolishQueueAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "high_quality_polish_queue_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"HighQualityPolishQueueAgent decision: {manifest['decision']}; "
            f"{manifest['queue_count']} shots, {manifest['provider_packet_count']} provider packets, "
            f"estimated external cost ${manifest['estimated_external_cost_usd']}."
        )
    if agent == "HighQualityProviderLaunchAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "high_quality_provider_launch_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"HighQualityProviderLaunchAgent prepared {manifest['selected_shot_count']} current-demo shots "
            f"across {manifest['selected_provider_count']} providers; first-pass cost "
            f"${manifest['estimated_first_pass_cost_usd']}. Report: {manifest['report']}"
        )
    if agent == "HighQualityProviderHandoffPackageAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "high_quality_provider_handoff_package_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("zip", {}).get("path", manifest_file)
        return (
            f"HighQualityProviderHandoffPackageAgent packaged {manifest['artifact_count']} artifacts; "
            f"zip entries: {manifest['zip']['entry_count']}. Zip: {manifest['zip']['path']}"
        )
    if agent == "HQProviderReturnSimAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "hq_provider_return_sim_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"HQProviderReturnSimAgent generated {manifest['generated_count']} simulated provider MP4 returns; "
            f"{manifest['accepted_count']} accepted, {manifest['rejected_count']} rejected. Report: {manifest['report']}"
        )
    if agent == "MCPVideoGatewayAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "mcp_video_gateway_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"MCPVideoGatewayAgent prepared {manifest['dispatch_count']} MCP video dispatch payloads; "
            f"{manifest['submitted_count']} submitted, {manifest['prepared_count']} prepared, "
            f"{manifest['blocked_count']} blocked. Report: {manifest['report']}"
        )
    if agent == "LocalPolishRenderAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "local_polish_render_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        return (
            f"LocalPolishRenderAgent rendered {manifest['rendered_count']} local polish MP4 candidates; "
            f"{manifest['accepted_count']} accepted, {manifest['rejected_count']} rejected. Report: {manifest['report']}"
        )
    if agent == "LocalPolishPromoteAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "local_polish_promote_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("master_video", manifest.get("report", manifest_file))
        return (
            f"LocalPolishPromoteAgent promoted {manifest['promoted_count']} accepted polish clips "
            f"into master preview: {manifest['master_video']}. Report: {manifest['report']}"
        )
    if agent == "ProductionReviewClosureAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "production_review_closure_agent.py"),
                "--task-id",
                task["id"],
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest.get("report", manifest_file)
        task["review"] = "Approved"
        task["status"] = "Approved"
        task["review_note"] = (
            f"ProductionReviewClosureAgent approved {manifest['approved_count']} evidence-backed tasks; "
            f"{manifest['kept_open_count']} remain open."
        )
        return (
            f"ProductionReviewClosureAgent applied closure: {manifest['approved_count']} approved, "
            f"{manifest['kept_open_count']} kept open. Report: {manifest['report']}"
        )
    if agent == "ExternalResultIngestAgent":
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "external_result_ingest_agent.py"),
                "--mode",
                "scan",
                "--quiet",
            ],
            check=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        manifest_file = result.stdout.strip()
        manifest = json.loads((WORKSPACE / manifest_file).read_text(encoding="utf-8"))
        task["manifest_file"] = manifest_file
        task["output_file"] = manifest_file
        return (
            f"ExternalResultIngestAgent prepared/scanned inbox: "
            f"{manifest['accepted_count']} accepted, {manifest['rejected_count']} rejected, "
            f"{manifest['unknown_count']} unknown results. Manifest: {manifest_file}"
        )
    return f"{agent} completed a simulated MVP pass for: {title}."


def api_payload() -> dict:
    return {
        "documents": list_documents(),
        "shots": SHOTS,
        "agents": AGENTS,
        "budget": BUDGET,
        "risks": RISKS,
        "tasks": load_tasks(),
        "pipeline": pipeline_status(),
    }


class Handler(BaseHTTPRequestHandler):
    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def send_json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            pipeline = pipeline_status()
            self.send_json(
                {
                    "project": "Kage Raksasa Scroll",
                    "documents": len(list_documents()),
                    "shots": len(SHOTS),
                    "agents": len(AGENTS),
                    "tasks": len(load_tasks()),
                    "pipeline_stage": pipeline["stage"],
                    "providers": pipeline["providers"]["provider_count"],
                    "master_preview_exists": pipeline["master"]["video"]["exists"],
                }
            )
            return
        if parsed.path == "/api/data":
            self.send_json(api_payload())
            return
        if parsed.path == "/api/pipeline":
            self.send_json(pipeline_status())
            return
        if parsed.path == "/api/documents":
            self.send_json(list_documents())
            return
        if parsed.path == "/api/tasks":
            self.send_json(load_tasks())
            return

        relative = "index.html" if parsed.path in {"/", ""} else parsed.path.lstrip("/")
        self.send_static(ROOT / relative)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/tasks":
            payload = self.read_body()
            tasks = load_tasks()
            now = int(time.time())
            task = {
                "id": next_task_id(tasks),
                "agent": payload.get("agent", "WriterAgent"),
                "title": payload.get("title", "Untitled task"),
                "prompt": payload.get("prompt", ""),
                "status": "Queued",
                "priority": payload.get("priority", "Medium"),
                "review": "Pending",
                "output": "",
                "created_at": now,
                "updated_at": now,
            }
            tasks.append(task)
            save_tasks(tasks)
            self.send_json(task, status=201)
            return

        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/run"):
            task_id = parsed.path.split("/")[3]
            tasks = load_tasks()
            for task in tasks:
                if task["id"] == task_id:
                    task["status"] = "Completed"
                    task["review"] = "Needs review"
                    task["output"] = simulate_agent_output(task)
                    task["updated_at"] = int(time.time())
                    if task.get("agent") == "ProductionReviewClosureAgent":
                        refreshed_tasks = load_tasks()
                        for refreshed_task in refreshed_tasks:
                            if refreshed_task["id"] == task_id:
                                refreshed_task.update(task)
                                break
                        else:
                            refreshed_tasks.append(task)
                        save_tasks(refreshed_tasks)
                    else:
                        save_tasks(tasks)
                    self.send_json(task)
                    return
            self.send_json({"error": "Task not found"}, status=404)
            return

        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/review"):
            task_id = parsed.path.split("/")[3]
            payload = self.read_body()
            decision = payload.get("decision", "Approved")
            tasks = load_tasks()
            for task in tasks:
                if task["id"] == task_id:
                    task["review"] = decision
                    task["status"] = "Approved" if decision == "Approved" else "Returned"
                    task["review_note"] = payload.get("note", "")
                    task["updated_at"] = int(time.time())
                    save_tasks(tasks)
                    self.send_json(task)
                    return
            self.send_json({"error": "Task not found"}, status=404)
            return

        self.send_json({"error": "Not found"}, status=404)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Kage Studio Hub running at http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
