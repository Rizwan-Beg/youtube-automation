"""
topic_manager.py — Topic Queue Manager

Reads topics from topics.json (each with title + description).
After processing, the topic is REMOVED from topics.json and
archived to processed_topics.json. This ensures the queue in
topics.json always reflects what's left to process.
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


def _load_topics_raw() -> dict:
    """Load the raw topics.json data as a dict."""
    if not TOPICS_FILE.exists():
        logger.error(f"❌ Topics file not found: {TOPICS_FILE}")
        return {"topics": []}

    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_topics_raw(data: dict) -> None:
    """Save topics data back to topics.json."""
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_topics() -> list[dict]:
    """
    Load the full topic list from topics.json.

    Returns:
        List of dicts, each with 'title' and 'description' keys.
    """
    data = _load_topics_raw()
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


def _load_processed() -> list[dict]:
    """
    Load the list of already-processed topics.

    Returns:
        List of dicts (title + description), or list of strings (legacy).
    """
    if not PROCESSED_TOPICS_FILE.exists():
        return []

    with open(PROCESSED_TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_processed(processed: list) -> None:
    """Save the processed topics list."""
    with open(PROCESSED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)


def get_next_topic() -> dict | None:
    """
    Return the first topic from topics.json.

    Returns:
        Dict with 'title' and 'description', or None if queue is empty.
    """
    all_topics = _load_topics()

    if not all_topics:
        logger.info("📭 Topic queue is empty — nothing to do.")
        return None

    topic = all_topics[0]
    logger.info(f"📋 Next topic: {topic['title']}")
    if topic["description"]:
        logger.info(f"   Description: {topic['description'][:80]}...")
    return topic


def mark_topic_processed(topic_title: str) -> None:
    """
    Mark a topic as processed:
    1. Remove it from topics.json
    2. Archive it to processed_topics.json

    Args:
        topic_title: The title of the topic to mark as processed.
    """
    # --- Remove from topics.json ---
    data = _load_topics_raw()
    raw_topics = data.get("topics", [])
    removed_topic = None

    updated_topics = []
    for item in raw_topics:
        # Match by title (works for both string and dict formats)
        if isinstance(item, str) and item == topic_title:
            removed_topic = {"title": item, "description": ""}
            continue  # skip — don't add to updated list
        elif isinstance(item, dict) and item.get("title") == topic_title:
            removed_topic = item
            continue  # skip
        updated_topics.append(item)

    data["topics"] = updated_topics
    _save_topics_raw(data)

    remaining = len(updated_topics)
    logger.info(f"🗑️  Removed from topics.json: {topic_title}")
    logger.info(f"   Remaining topics in queue: {remaining}")

    # --- Archive to processed_topics.json ---
    processed = _load_processed()
    if removed_topic:
        processed.append(removed_topic)
    else:
        # Fallback: if we couldn't find the full topic dict, store just the title
        processed.append({"title": topic_title, "description": ""})
    _save_processed(processed)

    logger.info(f"✅ Archived to processed_topics.json: {topic_title}")


def get_queue_status() -> dict:
    """Return a summary of the topic queue state."""
    all_topics = _load_topics()
    processed = _load_processed()
    return {
        "queue_count": len(all_topics),
        "processed_count": len(processed),
        "queue_topics": [t["title"] for t in all_topics],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    status = get_queue_status()
    print(f"Queue: {status['queue_count']} in queue, {status['processed_count']} processed")
    for t in status["queue_topics"]:
        print(f"  • {t}")
