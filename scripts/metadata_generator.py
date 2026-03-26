"""
metadata_generator.py — YouTube Metadata Generator (via Ollama / Llama3)

Generates YouTube title, description, and tags from a book title
using a local LLM through Ollama. Falls back to template-based
metadata if Ollama is unreachable.
"""

import json
import logging
from pathlib import Path

from scripts.config import METADATA_DIR, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def _call_ollama(prompt: str) -> str:
    """
    Send a prompt to Ollama and return the response text.
    Uses the ollama Python package.
    """
    try:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
    except Exception as e:
        logger.error(f"❌ Ollama call failed: {e}")
        raise


def _parse_llm_response(response_text: str) -> dict:
    """
    Parse the structured response from the LLM.
    Expects JSON with keys: title, description, tags
    Handles common LLM output quirks (extra text, markdown fences).
    """
    # Try to find JSON in the response
    text = response_text.strip()

    # Remove markdown code fences if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Try direct JSON parse
    try:
        data = json.loads(text)
        return {
            "title": str(data.get("title", "")),
            "description": str(data.get("description", "")),
            "tags": data.get("tags", []),
        }
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    import re
    json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "title": str(data.get("title", "")),
                "description": str(data.get("description", "")),
                "tags": data.get("tags", []),
            }
        except json.JSONDecodeError:
            pass

    logger.warning("⚠️  Could not parse LLM response as JSON, using raw text.")
    return {
        "title": text[:100],
        "description": text,
        "tags": [],
    }


def _generate_fallback_metadata(topic_title: str) -> dict:
    """
    Generate basic template metadata when Ollama is unavailable.
    """
    logger.warning("⚠️  Using fallback (template-based) metadata.")
    return {
        "title": f"{topic_title}",
        "description": (
            f"💰 {topic_title}\n\n"
            f"In this video, we break down a powerful money insight that "
            f"most people overlook. With simple math, real-world examples, "
            f"and compelling comparisons, you'll see why small financial "
            f"habits make a massive difference over time.\n\n"
            f"🔔 Subscribe for daily money tips!\n\n"
            f"#Money #Finance #Investing #PersonalFinance"
        ),
        "tags": [
            "money tips", "personal finance", "saving money",
            "investing", "financial freedom", "wealth building",
            "money habits", "compound interest", "budgeting",
            "get rich", "money mindset", "finance tips",
        ],
    }


def generate_metadata(topic_title: str, safe_name: str, description: str = "") -> dict:
    """
    Generate YouTube metadata (title, description, tags) for a topic.

    First attempts to use Ollama/Llama3 for AI-generated metadata.
    Falls back to templates if Ollama is unreachable.

    Args:
        topic_title: The video topic / title.
        safe_name:   Sanitized name (for filename).
        description: Additional context about the topic (book refs, tips, etc.).

    Returns:
        Dict with keys: title, description, tags
    """
    output_path = METADATA_DIR / f"{safe_name}.json"

    # Check if metadata already exists (resume support)
    if output_path.exists():
        logger.info(f"📋 Metadata already exists: {output_path.name}")
        with open(output_path, "r") as f:
            return json.load(f)

    logger.info(f"🤖 Generating metadata for: {topic_title}")

    description_context = ""
    if description:
        description_context = f"\nAdditional context: {description}\nUse this context to enrich the description with specific references, book mentions, and key ideas."

    prompt = f"""You are a YouTube SEO expert. Generate metadata for a finance/motivation video.

Video topic: "{topic_title}"{description_context}

Respond with ONLY a JSON object (no extra text) with these exact keys:
{{
  "title": "An engaging, click-worthy YouTube title (max 70 characters)",
  "description": "A compelling YouTube description (200-400 words) with emojis, timestamps placeholder, call to action, and relevant hashtags about money, saving, investing, and financial freedom",
  "tags": ["list", "of", "15-20", "relevant", "YouTube", "SEO", "tags"]
}}

Make the title attention-grabbing but not clickbait.
Include finance, money, investing, and personal growth keywords in tags.
"""

    try:
        response = _call_ollama(prompt)
        metadata = _parse_llm_response(response)
        # Always use the topic title as the YouTube title
        metadata["title"] = topic_title
        logger.info(f"✅ AI-generated metadata — Title: {metadata['title'][:60]}...")
    except Exception as e:
        logger.warning(f"⚠️  Ollama failed ({e}), using fallback metadata.")
        metadata = _generate_fallback_metadata(topic_title)

    # Ensure tags is a list
    if isinstance(metadata.get("tags"), str):
        metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]

    # Save to JSON
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Metadata saved: {output_path.name}")

    return metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test = generate_metadata("Saving $10 Daily Looks Useless — Until You See This", "saving_10_daily")
    print(json.dumps(test, indent=2))
