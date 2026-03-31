"""
video_processor.py — Video Post-Processing (Overlay + Trim)

Processes raw videos with FFmpeg:
1. Overlays channel name / "Subscribe & Like" text in the corner
   using a Pillow-generated PNG + FFmpeg overlay filter
   (avoids needing FFmpeg compiled with --enable-libfreetype)
2. Trims the last 2 seconds to remove NotebookLM self-advertisement
"""

import json
import logging
import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from pilmoji import Pilmoji
except ImportError:
    Pilmoji = None

from scripts.config import (
    VIDEOS_RAW_DIR,
    VIDEOS_CLEAN_DIR,
    CHANNEL_NAME,
    OVERLAY_TEXT,
    DRY_RUN,
    LOGS_DIR,
)

logger = logging.getLogger(__name__)

# How many seconds to trim from the end of the video
TRIM_SECONDS = 2.6

# NotebookLM watermark approximate location
DELOGO_X = 1100
DELOGO_Y = 620
DELOGO_W = 170
DELOGO_H = 80


def _check_ffmpeg() -> str:
    """Verify FFmpeg is installed and return its path."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise EnvironmentError(
            "FFmpeg not found. Install it via: brew install ffmpeg"
        )
    return ffmpeg_path


def _check_ffprobe() -> str:
    """Verify ffprobe is installed and return its path."""
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise EnvironmentError(
            "ffprobe not found. Install it via: brew install ffmpeg"
        )
    return ffprobe_path


def _get_video_duration(input_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    ffprobe = _check_ffprobe()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    logger.info(f"   Video duration: {duration:.2f}s")
    return duration


def _get_video_resolution(input_path: Path) -> tuple[int, int]:
    """Get video width and height using ffprobe."""
    ffprobe = _check_ffprobe()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "v:0",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    stream = info["streams"][0]
    width = int(stream["width"])
    height = int(stream["height"])
    logger.info(f"   Video resolution: {width}x{height}")
    return width, height


def _create_overlay_image(text: str, video_width: int, video_height: int, delogo_x: int = DELOGO_X, delogo_w: int = DELOGO_W) -> Path:
    """
    Create a transparent PNG with the overlay text using Pillow.
    This avoids needing FFmpeg's drawtext filter (which requires libfreetype).

    Returns:
        Path to the generated overlay PNG.
    """
    overlay_path = LOGS_DIR / "overlay_text.png"

    # Create a transparent image the same size as the video
    img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
    font_size = 28
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    font = None
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    # Measure text
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Position: EXACTLY OVER the blurred NotebookLM watermark
    # The watermark is at X = delogo_x, Y = DELOGO_Y with width delogo_w and height DELOGO_H
    if video_width >= delogo_x + delogo_w:
        # Center horizontally over the watermark
        x = delogo_x + (delogo_w - text_width) // 2
        
        # Center vertically over the watermark
        y = DELOGO_Y + (DELOGO_H - text_height) // 2
        
        # 💡 USER: TO ADJUST VERTICAL POSITION:
        # If you want it HIGHER: Subtract from y (e.g., y = y - 20)
        # If you want it LOWER:  Add to y      (e.g., y = y + 20)
        
        # 💡 USER: TO ADJUST HORIZONTAL POSITION:
        # If you want it LEFT:   Subtract from x (e.g., x = x - 20)
        # If you want it RIGHT:  Add to x      (e.g., x = x + 20)
    else:
        # Fallback if video is smaller than expected
        x = video_width - text_width - 20
        y = video_height - text_height - 20
    #for display heart shape after subscribe and like button
    if Pilmoji is not None:
        with Pilmoji(img) as pilmoji:
            # Draw text shadow (black border effect)
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    pilmoji.text((x + dx, y + dy), text, fill=(0, 0, 0, 200), font=font)
            # Draw main text (white)
            pilmoji.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    else:
        # Draw text shadow (black border effect)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((x + dx, y + dy), text, fill=(0, 0, 0, 200), font=font)
        # Draw main text (white)
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    img.save(str(overlay_path), "PNG")
    logger.info(f"   Overlay image created: {overlay_path.name}")
    return overlay_path


def process_video(safe_name: str, overlay_text: str = None) -> Path:
    """
    Process a raw video: add text overlay and trim last 2 seconds.

    Uses Pillow to create a PNG overlay image, then FFmpeg's overlay
    filter (always available, unlike drawtext which needs libfreetype).

    Args:
        safe_name:     Sanitized name (matches raw video filename).
        overlay_text:  Text to overlay in the corner. Defaults to
                       OVERLAY_TEXT from config.

    Returns:
        Path to the processed video file.

    Raises:
        FileNotFoundError: If the raw video doesn't exist.
        subprocess.CalledProcessError: If FFmpeg fails.
    """
    input_path = VIDEOS_RAW_DIR / f"{safe_name}_raw.mp4"
    output_path = VIDEOS_CLEAN_DIR / f"{safe_name}_final.mp4"

    if not input_path.exists():
        raise FileNotFoundError(f"Raw video not found: {input_path}")

    if DRY_RUN:
        logger.info("🏜️  DRY RUN — Skipping video processing.")
        shutil.copy2(str(input_path), str(output_path))
        return output_path

    ffmpeg = _check_ffmpeg()
    text = overlay_text or OVERLAY_TEXT

    # Get video info
    duration = _get_video_duration(input_path)
    width, height = _get_video_resolution(input_path)
    trim_end = max(duration - TRIM_SECONDS, 1.0)

    # Crop very little bit from left and right (e.g. 10 pixels each side)
    CROP_X = 10
    cropped_width = max(width - (CROP_X * 2), 1)
    adjusted_delogo_x = max(0, DELOGO_X - CROP_X)

    # Delogo requires a margin (usually 4px) to interpolate blur, so make sure it doesn't touch the very edge
    max_delogo_w = cropped_width - adjusted_delogo_x - 4
    adjusted_delogo_w = min(DELOGO_W, max_delogo_w)

    # Create the text overlay image using Pillow
    overlay_img = _create_overlay_image(text, cropped_width, height, adjusted_delogo_x, adjusted_delogo_w)

    # Build FFmpeg command:
    # - Input 0: the video
    # - Input 1: the overlay PNG
    # - filter_complex: trim video -> crop -> delogo the watermark -> overlay the PNG on top
    video_filter = (
        f"[0:v]trim=end={trim_end:.3f},setpts=PTS-STARTPTS[trimmed];"
        f"[trimmed]crop={cropped_width}:{height}:{CROP_X}:0[cropped];"
        f"[cropped]delogo=x={adjusted_delogo_x}:y={DELOGO_Y}:w={adjusted_delogo_w}:h={DELOGO_H}:show=0[blurred];"
        f"[blurred][1:v]overlay=0:0[out]"
    )
    audio_filter = f"atrim=end={trim_end:.3f},asetpts=PTS-STARTPTS"

    cmd = [
        ffmpeg,
        "-i", str(input_path),
        "-i", str(overlay_img),
        "-filter_complex", video_filter,
        "-af", audio_filter,
        "-map", "[out]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-y",
        str(output_path),
    ]

    logger.info(f"🎞️  Processing video: {input_path.name}")
    logger.info(f"   Overlay: {text}")
    logger.info(f"   Trimming: {duration:.2f}s → {trim_end:.2f}s (removing last {TRIM_SECONDS}s)")
    logger.info(f"   Output: {output_path.name}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Video processed: {output_path.name} ({size_mb:.1f} MB)")
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg failed:\n{e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error("❌ FFmpeg timed out after 10 minutes.")
        raise


def get_clean_video_path(safe_name: str) -> Path:
    """Return the expected path for a processed video."""
    return VIDEOS_CLEAN_DIR / f"{safe_name}_final.mp4"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _check_ffmpeg()
    _check_ffprobe()
    print("✅ FFmpeg and ffprobe are available. Video processor module loaded.")
    print(f"   Channel: {CHANNEL_NAME}")
    print(f"   Overlay: {OVERLAY_TEXT}")
    print(f"   Trim: last {TRIM_SECONDS}s")
