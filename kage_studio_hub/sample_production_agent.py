from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
STORYBOARD_DOC = ANIME_PROJECT / "影狩罗刹帖_StoryboardAgent分镜拆解_第二幕上v0.2_v0.2.md"
SEGMENT_NAME = "act2_01_sample"
SEGMENT_DIR = ANIME_PROJECT / "episode_segments" / SEGMENT_NAME
ASSET_DIR = SEGMENT_DIR / "visual_assets"
LAYER_DIR = SEGMENT_DIR / "layers"
SHOT_DIR = SEGMENT_DIR / "shots"
AUDIO_DIR = SEGMENT_DIR / "audio"
FINAL_DIR = SEGMENT_DIR / "final"

WIDTH = 1920
HEIGHT = 1080
FPS = 24
SECONDS_PER_SHOT = 2.0
FRAMES_PER_SHOT = int(FPS * SECONDS_PER_SHOT)
SAMPLE_RATE = 48_000


def find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


FONT_TITLE = find_font(44)
FONT_BODY = find_font(30)
FONT_SMALL = find_font(22)


def clean_filename(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "_", value).strip("_")


def ensure_dirs() -> None:
    for path in [ASSET_DIR, LAYER_DIR, SHOT_DIR, AUDIO_DIR, FINAL_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def write_toolchain_manifest() -> dict:
    manifest = {
        "segment": SEGMENT_NAME,
        "delivery": {
            "resolution": f"{WIDTH}x{HEIGHT}",
            "fps": FPS,
            "container": "mp4",
            "video_codec": "h264",
            "audio_codec": "aac",
        },
        "active_mode": "local_2d_limited_animation_fallback",
        "stage_routes": {
            "visual_design": {
                "active": "Pillow layered PNG generator",
                "preferred_external": ["OpenAI image generation", "Gemini image generation"],
                "purpose": "character sheets, monster silhouettes, background/keyframe references",
            },
            "shot_animation": {
                "active": "Python frame compositor + ffmpeg",
                "preferred_external": ["Remotion", "HyperFrames", "Kling image-to-video", "Seedance image-to-video"],
                "purpose": "shot-level motion, camera moves, I2V refinements, HTML-to-video rendering",
            },
            "audio": {
                "active": "Python temp WAV synthesizer",
                "preferred_external": ["DAW/SFX library", "voice/music generation service"],
                "purpose": "temp ambience, impacts, rhythm bed, later voice and music replacement",
            },
            "edit": {
                "active": "ffmpeg concat and mix",
                "preferred_external": ["Remotion composition", "NLE/XML export"],
                "purpose": "multi-video stitching, captions, versioning, final sample delivery",
            },
            "review": {
                "active": "manifest + markdown review",
                "preferred_external": ["Gemini multimodal review", "OpenAI multimodal review"],
                "purpose": "continuity, rating risk, originality, product readiness checks",
            },
        },
        "credential_policy": "External generators are optional. If API keys are absent, the local deterministic renderer remains the production fallback.",
    }
    path = SEGMENT_DIR / "toolchain_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def parse_storyboard_table(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    shots = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 8 or cells[0] in {"镜号", "---"} or not re.match(r"\d\d-\d\d\d", cells[0]):
            continue
        shots.append(
            {
                "id": cells[0],
                "scene": cells[1],
                "camera": cells[2],
                "action": cells[3],
                "fx": cells[4],
                "risk": cells[5],
                "cut": cells[6],
                "revision": cells[7],
            }
        )
    return shots


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        test = current + char
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def palette(shot: dict) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    scene = shot["scene"]
    if "废矿" in scene:
        return (22, 25, 23), (126, 154, 130), (230, 238, 214)
    if "沼泽" in scene or "村" in scene:
        return (19, 33, 31), (86, 136, 105), (220, 232, 211)
    if "荒寺" in scene:
        return (31, 28, 38), (139, 119, 176), (234, 226, 246)
    return (21, 25, 31), (125, 145, 171), (230, 234, 238)


def draw_bg_layer(shot: dict) -> Image.Image:
    bg, accent, light = palette(shot)
    image = Image.new("RGBA", (WIDTH, HEIGHT), (*bg, 255))
    draw = ImageDraw.Draw(image)
    scene = shot["scene"]

    for i in range(14):
        y = 130 + i * 62
        shade = tuple(max(0, min(255, c + i * 2)) for c in bg)
        draw.line((90, y, WIDTH - 90, y + 20), fill=(*shade, 190), width=4)

    if "废矿" in scene:
        draw.polygon([(160, 790), (620, 210), (1700, 780)], outline=(*accent, 255), width=8)
        draw.line((320, 780, 1620, 430), fill=(69, 86, 80, 240), width=12)
        draw.line((200, 820, 1700, 795), fill=(*light, 170), width=5)
    elif "沼泽" in scene or "村" in scene:
        draw.rectangle((0, 720, WIDTH, HEIGHT), fill=(24, 52, 47, 255))
        for n in range(10):
            draw.arc((120 + n * 170, 705, 340 + n * 170, 900), 185, 350, fill=(*accent, 230), width=5)
        draw.rectangle((150, 330, 620, 720), outline=(*accent, 200), width=6)
        draw.line((120, 330, 380, 190, 660, 330), fill=(*light, 150), width=6)
    elif "荒寺" in scene:
        draw.rectangle((0, 680, WIDTH, HEIGHT), fill=(36, 33, 45, 255))
        draw.polygon([(250, 770), (520, 210), (790, 770)], outline=(*accent, 255), width=8)
        draw.rectangle((430, 520, 620, 770), outline=(*light, 210), width=5)
        for n in range(5):
            draw.line((930, 245 + n * 95, 1600, 290 + n * 95), fill=(*accent, 210), width=5)
    else:
        draw.rectangle((360, 310, 1560, 820), outline=(*accent, 220), width=6)
    return image


def draw_character_layer(shot: dict, frame: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    _, accent, light = palette(shot)
    sid = shot["id"]
    t = frame / max(1, int(shot.get("frame_count", FRAMES_PER_SHOT)) - 1)
    bob = math.sin(t * math.tau * 1.2) * 8

    def ronin(cx: int, cy: int, scale: float = 1.0) -> None:
        h = int(210 * scale)
        draw.ellipse((cx - 54 * scale, cy - h - 54 * scale, cx + 54 * scale, cy - h + 54 * scale), fill=(26, 28, 30, 255), outline=(*light, 230), width=max(2, int(4 * scale)))
        draw.polygon([(cx - 120 * scale, cy - h - 22 * scale), (cx, cy - h - 105 * scale), (cx + 125 * scale, cy - h - 20 * scale)], fill=(28, 29, 28, 255), outline=(*light, 220))
        draw.line((cx, cy - h, cx, cy), fill=(*light, 230), width=max(5, int(7 * scale)))
        draw.line((cx - 35 * scale, cy - 80 * scale, cx + 155 * scale, cy - 145 * scale), fill=(*accent, 255), width=max(4, int(8 * scale)))
        draw.line((cx, cy, cx - 70 * scale, cy + 95 * scale), fill=(*light, 210), width=max(5, int(8 * scale)))
        draw.line((cx, cy, cx + 75 * scale, cy + 90 * scale), fill=(*light, 210), width=max(5, int(8 * scale)))

    def tobi(cx: int, cy: int, scale: float = 1.0) -> None:
        draw.ellipse((cx - 35 * scale, cy - 210 * scale, cx + 35 * scale, cy - 140 * scale), fill=(36, 37, 39, 255), outline=(*light, 210), width=max(2, int(3 * scale)))
        draw.line((cx, cy - 140 * scale, cx, cy + 10 * scale), fill=(*light, 220), width=max(4, int(6 * scale)))
        draw.rectangle((cx - 62 * scale, cy - 80 * scale, cx + 62 * scale, cy - 20 * scale), outline=(*accent, 240), width=max(3, int(5 * scale)))
        draw.line((cx - 35 * scale, cy - 120 * scale, cx - 130 * scale, cy - 170 * scale), fill=(*light, 190), width=max(3, int(5 * scale)))
        draw.line((cx, cy + 10 * scale, cx - 42 * scale, cy + 90 * scale), fill=(*light, 190), width=max(3, int(5 * scale)))
        draw.line((cx, cy + 10 * scale, cx + 48 * scale, cy + 85 * scale), fill=(*light, 190), width=max(3, int(5 * scale)))

    if sid in {"08-004", "08-005", "08-008"}:
        base_x = 660 + int(80 * t)
        body_y = 560 + bob
        for n in range(8):
            cx = base_x + n * 74
            draw.ellipse((cx, body_y + (n % 2) * 18, cx + 88, body_y + 82 + (n % 2) * 18), outline=(*light, 245), width=5)
        draw.line((base_x + 10, body_y + 10, base_x + 760, 350 + bob), fill=(*accent, 245), width=7)
        ronin(430, 800 + int(bob), 0.85)
    elif sid in {"11-003", "11-004", "11-005"}:
        mud_y = 760 - int(120 * t)
        draw.ellipse((790, mud_y - 250, 1130, mud_y + 90), outline=(*light, 240), width=8)
        draw.line((960, mud_y - 205, 875, mud_y + 80), fill=(*light, 220), width=7)
        draw.line((960, mud_y - 205, 1060, mud_y + 80), fill=(*light, 220), width=7)
        if sid == "11-004":
            for n in range(8):
                x = 1120 + n * 32
                y = 500 + math.sin(t * math.tau + n) * 25
                draw.arc((x, y, x + 45, y + 26), 0, 280, fill=(*accent, 230), width=4)
        ronin(460, 820 + int(bob), 0.75)
        tobi(1330, 820 - int(bob), 0.75)
    elif sid.startswith("12-"):
        tobi(760, 790 + int(bob), 0.85)
        ronin(1240, 805, 0.75)
    elif sid.startswith("14-"):
        ronin(760 + int(60 * t), 820 + int(bob), 0.8)
    else:
        ronin(760 + int(35 * t), 820 + int(bob), 0.8)
        tobi(1110 - int(22 * t), 820 - int(bob), 0.75)
    return image


def draw_fx_layer(shot: dict, frame: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    sid = shot["id"]
    _, accent, light = palette(shot)
    t = frame / max(1, int(shot.get("frame_count", FRAMES_PER_SHOT)) - 1)

    for n in range(55):
        x = (n * 83 + frame * 11) % WIDTH
        y = (n * 47 + frame * 19) % HEIGHT
        draw.line((x, y, x - 20, y + 55), fill=(155, 175, 190, 80), width=2)

    if sid == "08-007":
        alpha = int(150 + 80 * math.sin(t * math.pi))
        draw.polygon([(760, 860), (920, 300), (1130, 860)], fill=(235, 240, 210, alpha))
    if sid.startswith("12-"):
        color_shift = int(80 + 80 * math.sin(t * math.pi))
        draw.ellipse((820, 480, 1080, 640), fill=(40, 80 + color_shift, 70, 140), outline=(*light, 210), width=6)
    if sid == "14-002":
        for n in range(9):
            y = 250 + n * 70
            off = math.sin(t * math.tau + n) * 80
            draw.line((860, y, 1610 + off, y + 35), fill=(*accent, 160), width=5)
    if "V3" in shot["risk"] or "C" in shot["risk"]:
        draw.rectangle((1500, 92, 1815, 150), fill=(92, 35, 40, 210))
        draw.text((1524, 108), "ALT CUT SAFE", font=FONT_SMALL, fill=(255, 230, 220))
    return image.filter(ImageFilter.GaussianBlur(radius=0.2))


def save_visual_assets(shots: list[dict]) -> dict:
    assets: dict[str, str] = {}
    designs = {
        "rinzo_pose.png": ("凛藏", "ronin silhouette / short blade / rain hat"),
        "tobi_pose.png": ("鸢", "medicine box / compact archer pose"),
        "iron_centipede_silhouette.png": ("铁蜈蚣", "silhouette-first chain body"),
        "hirumaru_mud_form.png": ("蛭丸", "mud-form reveal / parasite cap 8"),
        "bony_biwa_space_warp.png": ("骨琵琶", "sound-led space skew"),
    }
    for filename, (title, note) in designs.items():
        image = Image.new("RGBA", (960, 540), (24, 26, 28, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((24, 24, 936, 516), outline=(218, 211, 184, 255), width=3)
        draw.text((50, 48), title, font=FONT_TITLE, fill=(238, 235, 215))
        draw.text((50, 112), note, font=FONT_SMALL, fill=(196, 211, 199))
        for n in range(7):
            draw.ellipse((180 + n * 70, 260 + (n % 2) * 18, 245 + n * 70, 325 + (n % 2) * 18), outline=(160, 185, 158, 255), width=4)
        path = ASSET_DIR / filename
        image.save(path)
        assets[filename] = str(path.relative_to(WORKSPACE))

    for shot in shots:
        shot["frame_count"] = frame_count_for_shot(shot)
        sid = clean_filename(shot["id"])
        bg = draw_bg_layer(shot)
        char = draw_character_layer(shot, 0)
        fx = draw_fx_layer(shot, 0)
        for name, layer in [("bg", bg), ("char", char), ("fx", fx)]:
            path = LAYER_DIR / f"{sid}_{name}.png"
            layer.save(path)
            assets[path.name] = str(path.relative_to(WORKSPACE))
    return assets


def frame_for_shot(shot: dict, frame: int, shot_index: int, total: int, frame_count: int) -> Image.Image:
    shot["frame_count"] = frame_count
    bg = draw_bg_layer(shot)
    char = draw_character_layer(shot, frame)
    fx = draw_fx_layer(shot, frame)
    image = Image.alpha_composite(bg, char)
    image = Image.alpha_composite(image, fx)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 72), fill=(10, 12, 14, 220))
    slate = f"{shot['id']}  {shot_index + 1:02d}/{total:02d}  {shot['scene']}  {shot['camera']}"
    draw.text((44, 18), slate, font=FONT_SMALL, fill=(240, 236, 215))
    lines = wrap_text(draw, shot["action"], FONT_BODY, 1450)
    subtitle = lines[0] if lines else shot["action"]
    draw.rectangle((72, HEIGHT - 132, WIDTH - 72, HEIGHT - 62), fill=(8, 10, 12, 190))
    draw.text((102, HEIGHT - 114), subtitle, font=FONT_BODY, fill=(244, 244, 238))
    return image.convert("RGB")


def encode_frames_to_mp4(frames, frame_count: int, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-frames:v",
        str(frame_count),
        str(output_path),
    ]
    proc = subprocess.Popen(cmd, cwd=str(WORKSPACE), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for frame in frames:
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    stderr = proc.stderr.read() if proc.stderr else b""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="ignore"))


def duration_for_shot(shot: dict) -> float:
    raw = shot.get("duration_seconds", SECONDS_PER_SHOT)
    try:
        duration = float(raw)
    except (TypeError, ValueError):
        duration = SECONDS_PER_SHOT
    return max(0.5, duration)


def frame_count_for_shot(shot: dict) -> int:
    return max(1, int(round(duration_for_shot(shot) * FPS)))


def render_shot_video(shot: dict, shot_index: int, total: int) -> Path:
    output_path = SHOT_DIR / f"{shot_index + 1:02d}_{shot['id']}.mp4"
    frame_count = frame_count_for_shot(shot)
    shot["frame_count"] = frame_count

    def frames():
        for frame in range(frame_count):
            yield frame_for_shot(shot, frame, shot_index, total, frame_count)

    encode_frames_to_mp4(frames(), frame_count, output_path)
    return output_path


def synthesize_audio(duration_seconds: float, output_path: Path) -> None:
    total_samples = int(duration_seconds * SAMPLE_RATE)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        for i in range(total_samples):
            t = i / SAMPLE_RATE
            drone = math.sin(2 * math.pi * 55 * t) * 0.18
            pulse = math.sin(2 * math.pi * 110 * t) * 0.08 if int(t * 2) % 4 == 0 else 0
            rain = math.sin(2 * math.pi * (740 + 17 * math.sin(t)) * t) * 0.025
            hit = 0.0
            if abs((t % 2.0) - 0.08) < 0.025:
                hit = math.sin(2 * math.pi * 180 * t) * 0.32 * (1 - abs((t % 2.0) - 0.08) / 0.025)
            sample = max(-0.7, min(0.7, drone + pulse + rain + hit))
            value = int(sample * 32767)
            wav.writeframesraw(value.to_bytes(2, "little", signed=True) + value.to_bytes(2, "little", signed=True))


def concat_videos(video_paths: list[Path], output_path: Path, audio_path: Path | None = None) -> None:
    concat_path = SEGMENT_DIR / "concat_list.txt"
    concat_path.write_text(
        "\n".join(f"file '{path.resolve().as_posix()}'" for path in video_paths),
        encoding="utf-8",
    )
    silent_path = FINAL_DIR / f"{SEGMENT_NAME}_silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(silent_path),
        ],
        check=True,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if audio_path:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(silent_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            check=True,
            cwd=str(WORKSPACE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        output_path.write_bytes(silent_path.read_bytes())


def render_visual_assets(task_id: str) -> dict:
    ensure_dirs()
    write_toolchain_manifest()
    shots = parse_storyboard_table(STORYBOARD_DOC)
    assets = save_visual_assets(shots)
    manifest = {
        "task_id": task_id,
        "stage": "visual_assets",
        "source": str(STORYBOARD_DOC.relative_to(WORKSPACE)),
        "asset_count": len(assets),
        "shot_count": len(shots),
        "assets": assets,
    }
    path = SEGMENT_DIR / "visual_assets_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def render_animation(task_id: str) -> dict:
    ensure_dirs()
    write_toolchain_manifest()
    shots = parse_storyboard_table(STORYBOARD_DOC)
    if not (SEGMENT_DIR / "visual_assets_manifest.json").exists():
        save_visual_assets(shots)
    video_paths = [render_shot_video(shot, idx, len(shots)) for idx, shot in enumerate(shots)]
    durations = [duration_for_shot(shot) for shot in shots]
    manifest = {
        "task_id": task_id,
        "stage": "shot_animation",
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "seconds_per_shot": SECONDS_PER_SHOT,
        "shot_count": len(shots),
        "duration_seconds": sum(durations),
        "shots": [
            {"shot_id": shot["id"], "video": str(path.relative_to(WORKSPACE)), "duration_seconds": duration}
            for shot, path, duration in zip(shots, video_paths, durations)
        ],
    }
    path = SEGMENT_DIR / "animation_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def render_audio(task_id: str) -> dict:
    ensure_dirs()
    write_toolchain_manifest()
    shots = parse_storyboard_table(STORYBOARD_DOC)
    duration = sum(duration_for_shot(shot) for shot in shots)
    audio_path = AUDIO_DIR / "temp_mix.wav"
    synthesize_audio(duration, audio_path)
    manifest = {
        "task_id": task_id,
        "stage": "temp_audio",
        "sample_rate": SAMPLE_RATE,
        "channels": 2,
        "duration_seconds": duration,
        "audio": str(audio_path.relative_to(WORKSPACE)),
        "note": "Temporary rain, drone, pulse, and impact track. No final voice acting.",
    }
    path = SEGMENT_DIR / "audio_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def render_edit(task_id: str) -> dict:
    ensure_dirs()
    toolchain = write_toolchain_manifest()
    animation_manifest_path = SEGMENT_DIR / "animation_manifest.json"
    audio_manifest_path = SEGMENT_DIR / "audio_manifest.json"
    if not animation_manifest_path.exists():
        render_animation(task_id)
    if not audio_manifest_path.exists():
        render_audio(task_id)
    animation_manifest = json.loads(animation_manifest_path.read_text(encoding="utf-8"))
    audio_manifest = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
    videos = [WORKSPACE / shot["video"] for shot in animation_manifest["shots"]]
    final_path = FINAL_DIR / f"{SEGMENT_NAME}_limited_animation.mp4"
    concat_videos(videos, final_path, WORKSPACE / audio_manifest["audio"])
    manifest = {
        "task_id": task_id,
        "stage": "final_edit",
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "shot_count": animation_manifest["shot_count"],
        "duration_seconds": animation_manifest["duration_seconds"],
        "audio": audio_manifest["audio"],
        "video": str(final_path.relative_to(WORKSPACE)),
        "shot_videos": [shot["video"] for shot in animation_manifest["shots"]],
        "toolchain": str((SEGMENT_DIR / "toolchain_manifest.json").relative_to(WORKSPACE)),
        "active_mode": toolchain["active_mode"],
        "review_status": "Needs DirectorAgent/RiskAgent review",
    }
    path = SEGMENT_DIR / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def render_review(task_id: str) -> dict:
    final_manifest_path = SEGMENT_DIR / "manifest.json"
    manifest = json.loads(final_manifest_path.read_text(encoding="utf-8")) if final_manifest_path.exists() else {}
    report = f"""# Product Review: {SEGMENT_NAME}

任务：{task_id}

结论：Needs review。该样段已经是可播放媒体产品原型，但还不是最终正片。

## 验收对象

- 视频：{manifest.get("video", "missing")}
- 镜头数：{manifest.get("shot_count", 0)}
- 时长：{manifest.get("duration_seconds", 0)} 秒
- 格式：1920x1080 / 24fps / H.264 MP4

## 导演判断

1. 可作为第一阶段产品演示样段，用于审节奏、镜头顺序、风险替代和后续配音/音乐。
2. 画面属于 2D 有限动画原型，已包含分层背景、角色剪影、FX、字幕、镜头运动和临时音频。
3. 风险镜头保持克制：08-003 不出现痛苦脸，11-004 寄生数量受控，12 段不表现儿童痛苦过程。

## 下一步

1. VisualDesignAgent 需要把剪影升级为定稿角色线稿。
2. AnimationAgent 需要为 08-004、11-003、14-002 增加关键姿势。
3. AudioAgent 后续替换为正式音效、音乐和配音。
4. EditAgent 可继续拼接 act2_02、act2_03 多段视频。
"""
    report_path = SEGMENT_DIR / "product_review.md"
    report_path.write_text(report, encoding="utf-8")
    review_manifest = {
        "task_id": task_id,
        "stage": "product_review",
        "report": str(report_path.relative_to(WORKSPACE)),
        "review": "Needs review",
        "video": manifest.get("video", ""),
    }
    path = SEGMENT_DIR / "review_manifest.json"
    path.write_text(json.dumps(review_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return review_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["visual", "animation", "audio", "edit", "review", "all"], required=True)
    parser.add_argument("--task-id", default="SAMPLE")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.stage == "visual":
        manifest = render_visual_assets(args.task_id)
        manifest_path = SEGMENT_DIR / "visual_assets_manifest.json"
    elif args.stage == "animation":
        manifest = render_animation(args.task_id)
        manifest_path = SEGMENT_DIR / "animation_manifest.json"
    elif args.stage == "audio":
        manifest = render_audio(args.task_id)
        manifest_path = SEGMENT_DIR / "audio_manifest.json"
    elif args.stage == "edit":
        manifest = render_edit(args.task_id)
        manifest_path = SEGMENT_DIR / "manifest.json"
    elif args.stage == "review":
        manifest = render_review(args.task_id)
        manifest_path = SEGMENT_DIR / "review_manifest.json"
    else:
        render_visual_assets(args.task_id)
        render_animation(args.task_id)
        render_audio(args.task_id)
        manifest = render_edit(args.task_id)
        manifest_path = SEGMENT_DIR / "manifest.json"

    if args.quiet:
        print(str(manifest_path.relative_to(WORKSPACE)))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
