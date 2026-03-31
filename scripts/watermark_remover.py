"""
watermark_remover.py — FFmpeg Watermark Removal

Removes the watermark from the bottom-right corner of videos
using FFmpeg's delogo filter, controlled via subprocess.
"""

import logging
import subprocess
import shutil
from pathlib import Path

from scripts.config import (
    VIDEOS_RAW_DIR,
    VIDEOS_CLEAN_DIR,
    DELOGO_X,
    DELOGO_Y,
    DELOGO_W,
    DELOGO_H,
    DRY_RUN,
)

logger = logging.getLogger(__name__)


def _check_ffmpeg() -> str:
    """
    Verify FFmpeg is installed and return its path.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise EnvironmentError(
            "FFmpeg not found. Install it via: brew install ffmpeg"
        )
    return ffmpeg_path


def remove_watermark(book_name: str) -> Path:
    """
    Remove the watermark from a raw video using FFmpeg delogo filter.

    The delogo region is configured via environment variables:
    DELOGO_X, DELOGO_Y, DELOGO_W, DELOGO_H

    Args:
        book_name: Sanitized book name.

    Returns:
        Path to the cleaned video file.

    Raises:
        FileNotFoundError: If the raw video doesn't exist.
        subprocess.CalledProcessError: If FFmpeg fails.
    """
    input_path = VIDEOS_RAW_DIR / f"{book_name}_raw.mp4"
    output_path = VIDEOS_CLEAN_DIR / f"{book_name}_final.mp4"

    if not input_path.exists():
        raise FileNotFoundError(f"Raw video not found: {input_path}")

    if DRY_RUN:
        logger.info("🏜️  DRY RUN — Skipping watermark removal.")
        # Copy file as-is for downstream testing
        shutil.copy2(str(input_path), str(output_path))
        return output_path

    ffmpeg = _check_ffmpeg()

    # Build the delogo filter string
    delogo_filter = f"delogo=x={DELOGO_X}:y={DELOGO_Y}:w={DELOGO_W}:h={DELOGO_H}"

    cmd = [
        ffmpeg,
        "-i", str(input_path),
        "-vf", delogo_filter,
        "-c:a", "copy",        # Copy audio without re-encoding
        "-y",                  # Overwrite output without asking
        str(output_path),
    ]

    logger.info(f"🎞️  Removing watermark from {input_path.name}...")
    logger.info(f"   Filter: {delogo_filter}")
    logger.info(f"   Output: {output_path.name}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10 minute timeout
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Watermark removed: {output_path.name} ({size_mb:.1f} MB)")
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg failed:\n{e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error("❌ FFmpeg timed out after 10 minutes.")
        raise


def get_clean_video_path(book_name: str) -> Path:
    """Return the expected path for a cleaned video."""
    return VIDEOS_CLEAN_DIR / f"{book_name}_final.mp4"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _check_ffmpeg()
    print("✅ FFmpeg is available. Watermark remover module loaded.")
    print(f"   Delogo region: x={DELOGO_X} y={DELOGO_Y} w={DELOGO_W} h={DELOGO_H}")
