"""
scheduler.py — Daily Pipeline Scheduler

Runs the main pipeline once per day at the configured time
using the `schedule` library. Designed for unattended operation.
"""

import time
import logging
import schedule

from scripts.config import SCHEDULE_TIME
from scripts.main_pipeline import run, setup_logging

logger = logging.getLogger(__name__)


def job():
    """
    Scheduled job: run the pipeline and log the result.
    """
    logger.info("⏰ Scheduled run triggered.")
    try:
        success = run()
        if success:
            logger.info("✅ Scheduled run completed successfully.")
        else:
            logger.info("📭 Scheduled run: queue was empty.")
    except Exception as e:
        logger.error(f"💥 Scheduled run failed: {e}")
        logger.exception("Full traceback:")


def start_scheduler():
    """
    Start the scheduler. Runs the pipeline daily at SCHEDULE_TIME.
    This function blocks forever.
    """
    setup_logging()

    logger.info("=" * 70)
    logger.info("🕐 YOUTUBE AUTO FACTORY — Scheduler Started")
    logger.info(f"   Daily run time: {SCHEDULE_TIME}")
    logger.info("   Press Ctrl+C to stop.")
    logger.info("=" * 70)

    # Schedule the job
    schedule.every().day.at(SCHEDULE_TIME).do(job)

    logger.info(f"📅 Next run: {schedule.next_run()}")

    # Run loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    except KeyboardInterrupt:
        logger.info("\n🛑 Scheduler stopped by user.")


if __name__ == "__main__":
    start_scheduler()
