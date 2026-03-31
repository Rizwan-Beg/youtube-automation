"""
cron_runner.py — Automated Daily Pipeline Runner (Cron-friendly)

Designed to be triggered repeatedly by a cron job (e.g., every 10 minutes).
Logic:
1. Checks if current time is within the allowed window (e.g., 21:30 - 23:50).
2. Checks if a successful video upload already occurred today.
3. If not, runs the main pipeline.
4. If successful, records today's date so it won't run again until tomorrow.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

from scripts.config import LOGS_DIR
from scripts.main_pipeline import run, setup_logging

logger = logging.getLogger("cron_runner")

# Configurable Time Window (24-hour format)
START_HOUR = 21
START_MINUTE = 30
END_HOUR = 23
END_MINUTE = 50

# File to track successful runs
LAST_RUN_FILE = LOGS_DIR / "last_upload_date.txt"


def is_within_time_window(now: datetime) -> bool:
    """Check if the current time is between start and end window."""
    start_time = now.replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
    end_time = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    
    return start_time <= now <= end_time


def already_ran_today(now: datetime) -> bool:
    """Check if the pipeline already succeeded today."""
    if not LAST_RUN_FILE.exists():
        return False
        
    try:
        last_date = LAST_RUN_FILE.read_text().strip()
        today_date = now.strftime("%Y-%m-%d")
        return last_date == today_date
    except Exception as e:
        logger.error(f"⚠️ Could not read last run file: {e}")
        return False


def mark_run_success(now: datetime) -> None:
    """Record today's date to prevent duplicate runs."""
    try:
        today_date = now.strftime("%Y-%m-%d")
        LAST_RUN_FILE.write_text(today_date)
        logger.info(f"✅ Marked pipeline as succeeded for today ({today_date}).")
    except Exception as e:
        logger.error(f"❌ Failed to write last run file: {e}")


def execute_cron_job() -> None:
    setup_logging()
    now = datetime.now()
    
    logger.info("=" * 60)
    logger.info(f"🕒 Cron Runner Triggered: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not is_within_time_window(now):
        logger.info(f"⏳ Optimization: Outside active window ({START_HOUR}:{START_MINUTE:02d} - {END_HOUR}:{END_MINUTE:02d}). Exiting.")
        return
        
    if already_ran_today(now):
        logger.info("✅ Pipeline already succeeded today. Exiting.")
        return
        
    logger.info("🚀 Time window active & no upload today. Starting pipeline...")
    
    # Run the main pipeline
    success = run()
    
    if success:
        mark_run_success(now)
        logger.info("🎉 Cron run completed successfully.")
    else:
        logger.warning("💥 Pipeline failed or queue empty. Will retry on next cron trigger.")

    logger.info("=" * 60)


if __name__ == "__main__":
    execute_cron_job()
