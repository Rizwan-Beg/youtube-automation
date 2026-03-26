"""
video_downloader.py — Video Download Handler

Provides utilities for saving Playwright downloads with proper naming.
This module is used by notebooklm_bot.py for download management.
"""

import logging
from pathlib import Path
from scripts.config import VIDEOS_RAW_DIR

logger = logging.getLogger(__name__)


def get_raw_video_path(book_name: str) -> Path:
    """
    Return the expected path for a raw downloaded video.

    Args:
        book_name: Sanitized book name.

    Returns:
        Path like videos_raw/bookname_raw.mp4
    """
    return VIDEOS_RAW_DIR / f"{book_name}_raw.mp4"


def video_already_exists(book_name: str) -> bool:
    """
    Check if a raw video already exists for this book.
    Useful for resuming interrupted pipelines.

    Args:
        book_name: Sanitized book name.

    Returns:
        True if the raw video file already exists and is non-empty.
    """
    path = get_raw_video_path(book_name)
    # Require at least 100 KB to avoid treating dry-run placeholders as real videos
    min_size = 100 * 1024  # 100 KB
    exists = path.exists() and path.stat().st_size > min_size
    if exists:
        logger.info(f"📹 Raw video already exists: {path.name} ({path.stat().st_size:,} bytes)")
    elif path.exists():
        size = path.stat().st_size
        logger.warning(
            f"⚠️  Found {path.name} but it's too small ({size} bytes) "
            f"— likely a placeholder. Will re-download."
        )
        path.unlink()  # Remove the invalid file
    return exists


def save_download(download, book_name: str) -> Path:
    """
    Save a Playwright download object as the raw video file.

    Args:
        download:  Playwright Download object.
        book_name: Sanitized book name.

    Returns:
        Path where the file was saved.
    """
    output_path = get_raw_video_path(book_name)
    download.save_as(str(output_path))
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"💾 Download saved: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Video downloader module loaded.")
    print(f"Videos will be saved to: {VIDEOS_RAW_DIR}")
