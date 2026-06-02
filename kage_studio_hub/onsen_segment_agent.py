from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import sample_production_agent as spa


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
SEGMENT_NAME = "onsen_01_sample"
SHOT_TABLE = ANIME_PROJECT / "影狩罗刹帖_雨夜温泉宿_试制片镜头表_v0.1.md"


def configure_segment() -> None:
    spa.STORYBOARD_DOC = SHOT_TABLE
    spa.SEGMENT_NAME = SEGMENT_NAME
    spa.SEGMENT_DIR = ANIME_PROJECT / "episode_segments" / SEGMENT_NAME
    spa.ASSET_DIR = spa.SEGMENT_DIR / "visual_assets"
    spa.LAYER_DIR = spa.SEGMENT_DIR / "layers"
    spa.SHOT_DIR = spa.SEGMENT_DIR / "shots"
    spa.AUDIO_DIR = spa.SEGMENT_DIR / "audio"
    spa.FINAL_DIR = spa.SEGMENT_DIR / "final"


def parse_onsen_table(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    shots = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 8 or cells[0] in {"镜号", "---"} or not re.fullmatch(r"\d{3}", cells[0]):
            continue
        duration = cells[1]
        duration_seconds = float(re.search(r"\d+", duration).group())
        camera = cells[2]
        visual = cells[3]
        action = cells[4]
        sound = cells[5]
        difficulty = cells[6]
        focus = cells[7]
        risk = "V2/M" if cells[0] in {"008", "010", "012", "015", "018"} else "M"
        if cells[0] in {"005", "007", "008", "012", "018", "019"}:
            risk = f"{risk}/S-shot"
        cut = "保留"
        if cells[0] in {"008", "010", "012", "015", "018"}:
            cut = "国际版减少血液和毒膜停留"
        shots.append(
            {
                "id": f"ON-{cells[0]}",
                "scene": "雨夜温泉宿",
                "camera": camera,
                "action": f"{visual}；{action}",
                "fx": f"{focus}; sound: {sound}; duration note: {duration}; difficulty: {difficulty}",
                "risk": risk,
                "cut": cut,
                "revision": "-",
                "duration_seconds": duration_seconds,
            }
        )
    return shots


def patch_parser() -> None:
    spa.parse_storyboard_table = parse_onsen_table


def run_stage(stage: str, task_id: str) -> tuple[dict, Path]:
    configure_segment()
    patch_parser()
    if stage == "visual":
        return spa.render_visual_assets(task_id), spa.SEGMENT_DIR / "visual_assets_manifest.json"
    if stage == "animation":
        return spa.render_animation(task_id), spa.SEGMENT_DIR / "animation_manifest.json"
    if stage == "audio":
        return spa.render_audio(task_id), spa.SEGMENT_DIR / "audio_manifest.json"
    if stage == "edit":
        return spa.render_edit(task_id), spa.SEGMENT_DIR / "manifest.json"
    if stage == "review":
        return spa.render_review(task_id), spa.SEGMENT_DIR / "review_manifest.json"
    if stage == "all":
        spa.render_visual_assets(task_id)
        spa.render_animation(task_id)
        spa.render_audio(task_id)
        return spa.render_edit(task_id), spa.SEGMENT_DIR / "manifest.json"
    raise ValueError(stage)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["visual", "animation", "audio", "edit", "review", "all"], required=True)
    parser.add_argument("--task-id", default="ONSEN")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest, path = run_stage(args.stage, args.task_id)
    if args.quiet:
        print(str(path.relative_to(WORKSPACE)))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
