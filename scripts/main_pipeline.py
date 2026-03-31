"""
main_pipeline.py — Main Orchestrator

Runs the full YouTube video production pipeline:
1. Get next topic from queue
2. Generate video via NotebookLM (topic-based prompt)
3. Process video (overlay text + trim last 2s)
4. Generate thumbnail
5. Generate metadata via LLM
6. Upload to YouTube
7. Mark topic as processed

Includes structured logging to both console and log file.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

from scripts.config import LOG_FILE
from scripts.topic_manager import get_next_topic, mark_topic_processed, sanitize_name
from scripts.notebooklm_bot import generate_from_topic
from scripts.video_processor import process_video
from scripts.thumbnail_generator import create_thumbnail
from scripts.metadata_generator import generate_metadata
from scripts.youtube_uploader import upload_video
from scripts.video_downloader import video_already_exists

logger = logging.getLogger("pipeline")


def setup_logging() -> None:
    """
    Configure logging to output to both console and a log file.
    """
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format, date_format))
    root.addHandler(console)

    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root.addHandler(file_handler)


def run() -> bool:
    """
    Execute one full pipeline run (process one topic).

    Returns:
        True if a topic was processed, False if queue was empty.
    """
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("🚀 YOUTUBE AUTO FACTORY — Pipeline Run Starting")
    logger.info(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # STEP 1: Get the next topic from the queue
    # ------------------------------------------------------------------
    logger.info("📋 STEP 1/7 — Checking topic queue...")
    topic_data = get_next_topic()

    if topic_data is None:
        logger.info("📭 No topics in queue. Pipeline idle.")
        return False

    topic = topic_data["title"]
    description = topic_data.get("description", "")
    safe_name = sanitize_name(topic)

    logger.info(f"   Topic: {topic}")
    logger.info(f"   Description: {description[:80]}..." if description else "   Description: (none)")
    logger.info(f"   Safe name: {safe_name}")

    try:
        # ------------------------------------------------------------------
        # STEP 2: Generate video via NotebookLM
        # ------------------------------------------------------------------
        if video_already_exists(safe_name):
            logger.info("⏭️  STEP 2/7 — Raw video exists, skipping NotebookLM.")
            from scripts.video_downloader import get_raw_video_path
            raw_video = get_raw_video_path(safe_name)
        else:
            logger.info("🤖 STEP 2/7 — NotebookLM automation...")
            raw_video = generate_from_topic(topic, safe_name, description)
        logger.info(f"   Raw video: {raw_video.name}")

        # ------------------------------------------------------------------
        # STEP 3: Process video (overlay + trim)
        # ------------------------------------------------------------------
        logger.info("🎞️  STEP 3/7 — Processing video (overlay + trim)...")
        clean_video = process_video(safe_name)
        logger.info(f"   Clean video: {clean_video.name}")

        # ------------------------------------------------------------------
        # STEP 4: Generate thumbnail
        # ------------------------------------------------------------------
        logger.info("🎨 STEP 4/7 — Generating thumbnail...")
        thumbnail = create_thumbnail(topic, safe_name)
        logger.info(f"   Thumbnail: {thumbnail.name}")

        # ------------------------------------------------------------------
        # STEP 5: Generate metadata
        # ------------------------------------------------------------------
        logger.info("🤖 STEP 5/7 — Generating metadata...")
        meta = generate_metadata(topic, safe_name, description)
        logger.info(f"   Title: {meta['title'][:60]}...")

        # ------------------------------------------------------------------
        # STEP 6: Upload to YouTube
        # ------------------------------------------------------------------
        logger.info("📤 STEP 6/7 — Uploading to YouTube...")
        video_id = upload_video(
            video_path=clean_video,
            title=meta["title"],
            description=meta["description"],
            tags=meta["tags"],
            thumbnail_path=thumbnail,
            privacy="public",
        )
        logger.info(f"   YouTube ID: {video_id}")

        # ------------------------------------------------------------------
        # STEP 7: Mark topic as processed
        # ------------------------------------------------------------------
        logger.info("📦 STEP 7/7 — Marking topic as processed...")
        mark_topic_processed(topic)

        # ------------------------------------------------------------------
        # Done!
        # ------------------------------------------------------------------
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 70)
        logger.info(f"🎉 PIPELINE COMPLETE — {topic[:50]}")
        logger.info(f"   Video: https://www.youtube.com/watch?v={video_id}")
        logger.info(f"   Duration: {elapsed:.0f} seconds ({elapsed / 60:.1f} min)")
        logger.info("=" * 70)
        return True

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error("=" * 70)
        logger.error(f"💥 PIPELINE FAILED — {topic[:50]}")
        logger.error(f"   Error: {e}")
        logger.error(f"   Duration: {elapsed:.0f} seconds")
        logger.error("=" * 70)
        logger.exception("Full traceback:")
        return False


if __name__ == "__main__":
    setup_logging()
    success = run()
    sys.exit(0 if success else 1)
