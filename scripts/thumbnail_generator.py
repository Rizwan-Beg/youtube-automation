"""
thumbnail_generator.py — AI YouTube Thumbnail Generator (Gemini API)

Uses Google Gemini API (Imagen 3) to generate professional YouTube
thumbnails. Falls back to a Pillow-based dark gradient design if
the API call fails.
"""

import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO

from scripts.config import THUMBNAILS_DIR, GEMINI_API_KEY, DRY_RUN

logger = logging.getLogger(__name__)

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


# ================= GEMINI API =================

def _generate_via_gemini_api(prompt: str, output_path: Path) -> Path:
    """
    Generate an image using Google Gemini API (gemini-3.1-flash-image-preview).

    Uses generate_content_stream with response_modalities=["IMAGE"].
    """
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in .env")

    client = genai.Client(api_key=GEMINI_API_KEY)

    logger.info("🎨 Calling Gemini API (gemini-3.1-flash-image-preview)...")
    logger.info(f"   Prompt: {prompt[:80]}...")

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    )

    image_data = None
    for chunk in client.models.generate_content_stream(
        model="gemini-3.1-flash-image-preview",
        contents=contents,
        config=config,
    ):
        if chunk.parts is None:
            continue
        if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
            image_data = chunk.parts[0].inline_data.data
            break

    if not image_data:
        raise RuntimeError("Gemini API returned no image data.")

    # Save and resize to YouTube thumbnail dimensions
    img = Image.open(BytesIO(image_data))
    img = img.convert("RGB").resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
    img.save(str(output_path), "PNG", quality=95)

    logger.info(f"✅ Gemini API image saved: {output_path.name}")
    return output_path


# ================= FALLBACK =================

def _get_font(size: int):
    """Load a bold font, falling back to Pillow default."""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _generate_fallback_thumbnail(topic_title: str, output_path: Path) -> Path:
    """
    Generate a basic Pillow-based thumbnail as fallback.
    Dark gradient background with bold title text.
    """
    logger.warning("⚠️  Using fallback Pillow thumbnail (Gemini API failed).")

    img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Dark gradient background
    for y in range(THUMB_HEIGHT):
        ratio = y / THUMB_HEIGHT
        r = int(10 * (1 - ratio) + 5 * ratio)
        g = int(10 * (1 - ratio) + 5 * ratio)
        b = int(46 * (1 - ratio) + 16 * ratio)
        draw.line([(0, y), (THUMB_WIDTH, y)], fill=(r, g, b))

    # Orange accent bar
    accent = (255, 165, 0)
    draw.rectangle([(0, 0), (THUMB_WIDTH, 6)], fill=accent)

    # Title text
    font = _get_font(56)
    text = topic_title.upper()
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= THUMB_WIDTH - 160:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_h = 72
    start_y = (THUMB_HEIGHT - len(lines) * line_h) / 2
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        x = (THUMB_WIDTH - (bbox[2] - bbox[0])) / 2
        y = start_y + i * line_h
        draw.text((x + 3, y + 3), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)

    img.save(str(output_path), "PNG")
    logger.info(f"✅ Fallback thumbnail saved: {output_path.name}")
    return output_path


# ================= ENHANCE =================

def _enhance_image(img: Image.Image) -> Image.Image:
    """Apply contrast and sharpness enhancement."""
    img = ImageEnhance.Contrast(img).enhance(1.4)
    img = ImageEnhance.Sharpness(img).enhance(1.8)
    return img


# ================= MAIN =================

def create_thumbnail(topic_title: str, safe_name: str) -> Path:
    """
    Generate a YouTube thumbnail using Gemini API (Imagen 3).
    Falls back to Pillow-based design on failure.

    Args:
        topic_title: Human-readable topic title.
        safe_name:   Sanitized name for filename.

    Returns:
        Path to the saved thumbnail PNG.
    """
    output_path = THUMBNAILS_DIR / f"{safe_name}.png"

    logger.info(f"🎨 Generating thumbnail for: {topic_title}")

    if DRY_RUN:
        logger.info("🏜️  DRY RUN — Generating fallback thumbnail.")
        return _generate_fallback_thumbnail(topic_title, output_path)

    # Build the prompt
    prompt = (
        f"minimal cinematic youtube thumbnail for topic \"{topic_title}\" — "
        f"make a minimalistic professional thumbnail that increases human click on video, "
        f"no text overlays, bold visual composition, dramatic lighting"
    )

    try:
        _generate_via_gemini_api(prompt, output_path)

        # Enhance the AI-generated image
        img = Image.open(output_path).convert("RGB")
        img = _enhance_image(img)
        img.save(str(output_path), "PNG", quality=95)
        logger.info(f"✅ Thumbnail finalized: {output_path.name}")

    except Exception as e:
        logger.error(f"❌ Gemini API thumbnail failed: {e}")
        _generate_fallback_thumbnail(topic_title, output_path)

    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_thumbnail("Most People Ignore This And Stay Broke", "test_thumb")