"""
process_existing.py — Reprocess existing raw videos

Runs video processing, thumbnail generation, and metadata generation
on any raw videos already in videos_raw/ without re-running NotebookLM.
"""

import logging
from pathlib import Path
from scripts.config import VIDEOS_RAW_DIR
from scripts.video_processor import process_video
from scripts.thumbnail_generator import create_thumbnail
from scripts.metadata_generator import generate_metadata


def setup_test_logging():
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format, date_format))
    if not root.handlers:
        root.addHandler(console)


def run_tests():
    setup_test_logging()
    logger = logging.getLogger("test_existing")

    raw_videos = list(VIDEOS_RAW_DIR.glob("*_raw.mp4"))
    if not raw_videos:
        logger.info("No raw videos found in videos_raw/")
        return

    for raw_video_path in raw_videos:
        # File format is {safe_name}_raw.mp4
        safe_name = raw_video_path.name.replace("_raw.mp4", "")
        # Create a display topic by replacing underscores with spaces
        topic = safe_name.replace("_", " ").title()

        logger.info("=" * 70)
        logger.info(f"▶️ Processing existing raw video: {safe_name}")
        logger.info("=" * 70)

        try:
            # 1. Video Processing (Crop, Delogo, Overlay, Trim)
            logger.info("🎞️  STEP 1 — Processing video (crop + delogo + overlay + trim)...")
            clean_video = process_video(safe_name)
            logger.info(f"   Success! Output saved to: {clean_video}")

            # 2. Thumbnail Generation
            logger.info("🎨 STEP 2 — Generating thumbnail...")
            thumbnail = create_thumbnail(topic, safe_name)
            logger.info(f"   Success! Thumbnail saved to: {thumbnail}")

            # 3. Metadata Generation
            logger.info("🤖 STEP 3 — Generating metadata via Ollama...")
            meta = generate_metadata(topic, safe_name)
            logger.info(f"   Success! Title: {meta['title']}")
            logger.info(f"   Tags: {', '.join(meta['tags'])}")

        except Exception as e:
            logger.error(f"❌ Failed to process {safe_name}: {e}")


if __name__ == "__main__":
    run_tests()
