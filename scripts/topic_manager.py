"""
topic_manager.py — Topic Queue Manager

Reads topics from topics.json (each with title + description),
tracks processed topics in processed_topics.json, and provides
the next unprocessed topic as a dict.
"""

import re
import json
import logging
from pathlib import Path
from scripts.config import TOPICS_FILE, PROCESSED_TOPICS_FILE

logger = logging.getLogger(__name__)


def sanitize_name(topic: str) -> str:
    """
    Convert a topic string into a safe, filesystem-friendly name.
    Replaces whitespace/special chars with underscores and lowercases.
    """
    clean = re.sub(r"[^a-zA-Z0-9\-]", "_", topic)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean.lower()[:80]  # Cap length for filesystem safety


def _load_topics() -> list[dict]:
    """
    Load the full topic list from topics.json.

    Returns:
        List of dicts, each with 'title' and 'description' keys.
    """
    if not TOPICS_FILE.exists():
        logger.error(f"❌ Topics file not found: {TOPICS_FILE}")
        return []

    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_topics = data.get("topics", [])

    # Normalise: support both old format (plain strings) and new format (dicts)
    normalised = []
    for item in raw_topics:
        if isinstance(item, str):
            normalised.append({"title": item, "description": ""})
        elif isinstance(item, dict):
            normalised.append({
                "title": item.get("title", ""),
                "description": item.get("description", ""),
            })
    return normalised


def _load_processed() -> list[str]:
    """Load the list of already-processed topic titles."""
    if not PROCESSED_TOPICS_FILE.exists():
        return []

    with open(PROCESSED_TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_processed(processed: list[str]) -> None:
    """Save the processed topics list."""
    with open(PROCESSED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)


def get_next_topic() -> dict | None:
    """
    Return the next unprocessed topic from topics.json.

    Returns:
        Dict with 'title' and 'description', or None if all processed.
    """
    all_topics = _load_topics()
    processed = _load_processed()

    for topic in all_topics:
        if topic["title"] not in processed:
            logger.info(f"📋 Next topic: {topic['title']}")
            if topic["description"]:
                logger.info(f"   Description: {topic['description'][:80]}...")
            return topic

    logger.info("📭 All topics have been processed — nothing to do.")
    return None


def mark_topic_processed(topic_title: str) -> None:
    """
    Mark a topic as processed by adding its title to processed_topics.json.
    """
    processed = _load_processed()
    if topic_title not in processed:
        processed.append(topic_title)
        _save_processed(processed)
        logger.info(f"✅ Marked as processed: {topic_title}")


def get_queue_status() -> dict:
    """Return a summary of the topic queue state."""
    all_topics = _load_topics()
    processed = _load_processed()
    pending = [t for t in all_topics if t["title"] not in processed]
    return {
        "total_count": len(all_topics),
        "processed_count": len(processed),
        "pending_count": len(pending),
        "pending_topics": [t["title"] for t in pending],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    status = get_queue_status()
    print(f"Queue: {status['pending_count']} pending, {status['processed_count']} processed")
    for t in status["pending_topics"]:
        print(f"  • {t}")
