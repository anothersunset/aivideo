#!/usr/bin/env python3
"""TASK-058 HQProviderReturnSimAgent
Generates SIMULATED HQ provider-return MP4s from local shot outputs.
NO external API call. NO HTTP submit/poll. NO API key. NO secrets.
Verified against repo schema: tool_jobs/{segment}/shot_jobs.json -> jobs[].
"""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME = WORKSPACE / "anime_project"
PIPE = ANIME / "pipeline"
TOOL_JOBS = PIPE / "tool_jobs"
INBOX = PIPE / "external_results" / "inbox"
MANIFEST_DIR = PIPE / "external_results" / "manifests"
MANIFEST = MANIFEST_DIR / "simulated_hq_provider_returns.json"

W, H, FPS = 1920, 1080, 24
TARGETS = [
    {"segment": "onsen_01_sample", "shot_id": "ON-008", "provider": "kling_i2v"},
    {"segment": "act2_01_sample",  "shot_id": "08-004", "provider": "runway"},
]

# Light cinematic grade only - no story/character changes.
# fps=24 -> ffprobe r_frame_rate "24/1"; scale+crop guarantees EXACT 1920x1080.
def provider_vf(provider):
    grades = {
        "kling_i2v": "eq=contrast=1.12:saturation=1.10:brightness=-0.01,unsharp=5:5:0.6",
        "runway":    "eq=contrast=1.08:saturation=1.06,unsharp=3:3:0.45",
    }
    grade = grades.get(provider, "eq=contrast=1.06:saturation=1.05,unsharp=3:3:0.4")
    return (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},{grade},format=yuv420p")

def rel(p):
    return str(p.relative_to(WORKSPACE))

def load_jobs(segment):
    path = TOOL_JOBS / segment / "shot_jobs.json"
    return json.loads(path.read_text(encoding="utf-8"))["jobs"]

def find_job(segment, shot_id):
    for j in load_jobs(segment):
        if j.get("shot_id") == shot_id:
            return j
    raise KeyError(f"{segment}/{shot_id} not in shot_jobs.json")

def resolve_local(raw):
    # current_local_output uses Windows backslashes; normalize for cross-platform.
    p = Path(raw.replace("\\\\", "/").replace("\\", "/"))
    return p if p.is_absolute() else WORKSPACE / p

def probe_duration(path):
    out = subprocess.run(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","default=nw=1:nk=1",str(path)],
        check=True, capture_output=True, text=True).stdout.strip()
    return round(float(out), 3)

def render(src, dst, seconds, provider):
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-y","-i",str(src),"-t",f"{seconds:.3f}",
        "-vf",provider_vf(provider),"-r",str(FPS),
        "-c:v","libx264","-preset","veryfast","-crf","20",
        "-pix_fmt","yuv420p","-an","-movflags","+faststart",str(dst)],
        check=True, cwd=str(WORKSPACE))
    assert dst.exists() and dst.stat().st_size > 100_000, f"output too small: {dst}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    returns = []
    for t in TARGETS:
        seg, shot, prov = t["segment"], t["shot_id"], t["provider"]
        job = find_job(seg, shot)
        src = resolve_local(job["current_local_output"])
        if not src.exists():
            raise FileNotFoundError(f"local source not found: {src}")
        duration = float(job["duration_seconds"])
        dst = INBOX / prov / seg / shot / f"{shot}_{prov}.mp4"
        render(src, dst, duration, prov)
        returns.append({
            "task_id": "TASK-058", "provider": prov, "segment": seg, "shot_id": shot,
            "source": rel(src), "output": rel(dst),
            "width": W, "height": H, "fps": FPS,
            "target_duration_seconds": round(duration, 3),
            "actual_duration_seconds": probe_duration(dst),
            "enhancement": "contrast+saturation+sharpen cinematic grade only",
            "mode": "simulated_provider_return_no_external_api_call",
            "external_api_called": False})
        if not args.quiet:
            print(f"[sim] {prov}/{seg}/{shot} -> {rel(dst)}")
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({
        "task_id": "TASK-058",
        "stage": "hq_provider_return_simulation",
        "mode": "simulated_provider_return_no_external_api_call",
        "external_api_called": False,
        "return_count": len(returns),
        "returns": returns,
        "next_step": "Run ExternalResultIngestAgent scan mode.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"[sim] wrote {rel(MANIFEST)}")

if __name__ == "__main__":
    main()
