from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
ANIME_PROJECT = WORKSPACE / "anime_project"
MEDIA_DIR = ANIME_PROJECT / "media" / "act2_storyboard_v02"
BOARDS_DIR = MEDIA_DIR / "boards"
FRAMES_DIR = MEDIA_DIR / "frames"
STORYBOARD_DOC = ANIME_PROJECT / "影狩罗刹帖_StoryboardAgent分镜拆解_第二幕上v0.2_v0.2.md"

WIDTH = 1920
HEIGHT = 1080
FPS = 12
SECONDS_PER_SHOT = 2
FRAMES_PER_SHOT = FPS * SECONDS_PER_SHOT


def find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = find_font(46)
FONT_BODY = find_font(31)
FONT_SMALL = find_font(24)
FONT_TINY = find_font(19)


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


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines = []
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


def palette_for_shot(shot: dict) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    scene = shot["scene"]
    if "废矿" in scene:
        return (31, 34, 32), (145, 163, 135), (235, 242, 220)
    if "沼泽" in scene or "村" in scene:
        return (24, 36, 35), (92, 139, 113), (221, 233, 210)
    if "荒寺" in scene:
        return (34, 31, 40), (148, 126, 178), (236, 226, 245)
    return (28, 32, 39), (124, 148, 174), (230, 235, 242)


def draw_composition(draw: ImageDraw.ImageDraw, shot: dict, idx: int, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    bg, accent, light = palette_for_shot(shot)
    draw.rectangle(box, fill=bg, outline=(210, 210, 190), width=4)
    scene = shot["scene"]
    shot_id = shot["id"]

    for i in range(0, 9):
        y = y1 + 40 + i * 88
        color = tuple(min(255, c + i * 3) for c in bg)
        draw.line([(x1 + 40, y), (x2 - 40, y + 20)], fill=color, width=5)

    if "废矿" in scene:
        draw.polygon([(x1 + 120, y2 - 90), (x1 + 520, y1 + 150), (x2 - 130, y2 - 120)], outline=accent, width=8)
        draw.line([(x1 + 260, y2 - 110), (x2 - 230, y1 + 230)], fill=(65, 80, 74), width=14)
        if shot_id in {"08-004", "08-005", "08-008"}:
            body_y = y1 + 430
            for n in range(8):
                cx = x1 + 650 + n * 70
                draw.ellipse((cx, body_y + n % 2 * 18, cx + 85, body_y + 82 + n % 2 * 18), outline=light, width=5)
            draw.line([(x1 + 690, body_y + 20), (x2 - 210, y1 + 260)], fill=accent, width=5)
        if shot_id == "08-007":
            draw.polygon([(x1 + 640, y2 - 80), (x1 + 820, y1 + 310), (x1 + 1040, y2 - 80)], fill=(235, 236, 210))
    elif "沼泽" in scene or "村" in scene:
        for n in range(9):
            draw.arc((x1 + 110 + n * 170, y2 - 310, x1 + 300 + n * 170, y2 - 130), 190, 350, fill=accent, width=6)
        if shot_id in {"11-003", "11-004", "11-005"}:
            draw.ellipse((x1 + 780, y1 + 290, x1 + 1110, y1 + 720), outline=light, width=8)
            draw.line([(x1 + 945, y1 + 340), (x1 + 860, y1 + 720)], fill=light, width=7)
            draw.line([(x1 + 945, y1 + 340), (x1 + 1050, y1 + 720)], fill=light, width=7)
        if shot_id.startswith("12-"):
            draw.ellipse((x1 + 740, y1 + 390, x1 + 1120, y1 + 650), outline=(225, 230, 218), width=9)
            draw.ellipse((x1 + 815, y1 + 450, x1 + 1045, y1 + 600), fill=(52, 78, 67), outline=accent, width=4)
    elif "荒寺" in scene:
        draw.polygon([(x1 + 260, y2 - 100), (x1 + 520, y1 + 200), (x1 + 780, y2 - 100)], outline=accent, width=8)
        draw.rectangle((x1 + 440, y1 + 530, x1 + 620, y2 - 100), outline=light, width=5)
        for n in range(5):
            off = int(math.sin((idx + n) * 0.9) * 30)
            draw.line([(x1 + 920, y1 + 260 + n * 95), (x2 - 260 + off, y1 + 310 + n * 95)], fill=accent, width=5)
        if shot_id == "14-003":
            draw.line([(x1 + 780, y1 + 730), (x1 + 1120, y1 + 665)], fill=light, width=10)
    else:
        draw.rectangle((x1 + 520, y1 + 330, x2 - 520, y2 - 220), outline=accent, width=8)

    if "CU" in shot["camera"] or "Insert" in shot["camera"]:
        draw.rectangle((x1 + 210, y1 + 140, x2 - 210, y2 - 140), outline=(238, 238, 220), width=6)
    if "WS" in shot["camera"] or "LS" in shot["camera"]:
        draw.rectangle((x1 + 80, y1 + 80, x2 - 80, y2 - 80), outline=(130, 130, 120), width=3)

    if "V3" in shot["risk"] or "C" in shot["risk"]:
        draw.rectangle((x2 - 300, y1 + 40, x2 - 55, y1 + 100), fill=(92, 35, 40))
        draw.text((x2 - 278, y1 + 54), "RISK ALT", font=FONT_SMALL, fill=(255, 230, 220))


def render_board(shot: dict, idx: int, total: int, path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), (18, 19, 22))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(20, 22, 25))
    draw.rectangle((52, 52, WIDTH - 52, HEIGHT - 52), outline=(214, 207, 181), width=3)
    draw_composition(draw, shot, idx, (92, 128, WIDTH - 92, 760))

    slate = f"{shot['id']}  {idx + 1:02d}/{total:02d}  {shot['scene']}  {shot['camera']}"
    draw.rectangle((92, 790, WIDTH - 92, 852), fill=(35, 38, 42))
    draw.text((118, 804), slate, font=FONT_BODY, fill=(242, 236, 210))

    y = 870
    for line in wrap_text(draw, shot["action"], FONT_BODY, 1500)[:2]:
        draw.text((118, y), line, font=FONT_BODY, fill=(238, 238, 232))
        y += 42
    meta = f"FX: {shot['fx']}    Risk: {shot['risk']}    Cut: {shot['cut']}"
    for line in wrap_text(draw, meta, FONT_SMALL, 1600)[:2]:
        draw.text((118, y + 12), line, font=FONT_SMALL, fill=(190, 203, 198))
        y += 34
    if shot["revision"] != "-":
        draw.text((118, HEIGHT - 78), f"REV: {shot['revision']}", font=FONT_TINY, fill=(255, 213, 170))
    image.save(path, quality=95)


def render_frames(board_paths: list[Path], frame_dir: Path) -> int:
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_index = 0
    for shot_index, board_path in enumerate(board_paths):
        board = Image.open(board_path).convert("RGB")
        for local in range(FRAMES_PER_SHOT):
            t = local / max(1, FRAMES_PER_SHOT - 1)
            zoom = 1.0 + 0.035 * t
            crop_w = int(WIDTH / zoom)
            crop_h = int(HEIGHT / zoom)
            drift = -1 if shot_index % 2 else 1
            left = int((WIDTH - crop_w) * (0.5 + 0.18 * drift * (t - 0.5)))
            top = int((HEIGHT - crop_h) * 0.5)
            frame = board.crop((left, top, left + crop_w, top + crop_h)).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            frame.save(frame_dir / f"frame_{frame_index:05d}.png")
            frame_index += 1
    return frame_index


def encode_video(frame_dir: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frame_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, cwd=str(WORKSPACE), stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def render_animatic(task_id: str) -> dict:
    shots = parse_storyboard_table(STORYBOARD_DOC)
    if not shots:
        raise RuntimeError(f"No storyboard rows found in {STORYBOARD_DOC}")
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for old in BOARDS_DIR.glob("*.png"):
        old.unlink()
    for old in FRAMES_DIR.glob("*.png"):
        old.unlink()

    board_paths = []
    for idx, shot in enumerate(shots):
        path = BOARDS_DIR / f"{idx + 1:02d}_{shot['id']}.png"
        render_board(shot, idx, len(shots), path)
        board_paths.append(path)

    frame_count = render_frames(board_paths, FRAMES_DIR)
    video_path = MEDIA_DIR / "act2_storyboard_v02_animatic.mp4"
    encode_video(FRAMES_DIR, video_path)
    manifest = {
        "task_id": task_id,
        "source": str(STORYBOARD_DOC.relative_to(WORKSPACE)),
        "shot_count": len(shots),
        "fps": FPS,
        "seconds_per_shot": SECONDS_PER_SHOT,
        "duration_seconds": len(shots) * SECONDS_PER_SHOT,
        "frame_count": frame_count,
        "boards_dir": str(BOARDS_DIR.relative_to(WORKSPACE)),
        "frames_dir": str(FRAMES_DIR.relative_to(WORKSPACE)),
        "video": str(video_path.relative_to(WORKSPACE)),
        "boards": [str(path.relative_to(WORKSPACE)) for path in board_paths],
    }
    manifest_path = MEDIA_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="ANIMATIC")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    manifest = render_animatic(args.task_id)
    if args.quiet:
        print(str((MEDIA_DIR / "manifest.json").relative_to(WORKSPACE)))
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
