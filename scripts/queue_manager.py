"""
queue_manager.py — PDF Queue Manager

Scans the books_queue/ folder for PDF files, returns the next one
to process, and moves completed PDFs to processed_books/.
"""

import re
import shutil
import logging
from pathlib import Path
from scripts.config import BOOKS_QUEUE_DIR, PROCESSED_BOOKS_DIR

logger = logging.getLogger(__name__)


def sanitize_name(name: str) -> str:
    """
    Convert a filename into a safe, filesystem-friendly base name.
    Strips extension, replaces whitespace/special chars with underscores,
    and lowercases the result.
    """
    # Remove file extension
    stem = Path(name).stem
    # Replace non-alphanumeric (except hyphens) with underscores
    clean = re.sub(r"[^a-zA-Z0-9\-]", "_", stem)
    # Collapse multiple underscores
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean.lower()


def get_next_book() -> Path | None:
    """
    Scan books_queue/ for the first PDF (sorted alphabetically).

    Returns:
        Path to the PDF file, or None if the queue is empty.
    """
    pdfs = sorted(BOOKS_QUEUE_DIR.glob("*.pdf"))
    if not pdfs:
        logger.info("📭 Book queue is empty — nothing to process.")
        return None

    next_pdf = pdfs[0]
    logger.info(f"📖 Next book in queue: {next_pdf.name}")
    return next_pdf


def mark_as_processed(pdf_path: Path) -> Path:
    """
    Move a PDF from books_queue/ to processed_books/.

    Args:
        pdf_path: Path to the PDF to move.

    Returns:
        New path of the moved file.
    """
    destination = PROCESSED_BOOKS_DIR / pdf_path.name
    # Handle name collision — append suffix
    counter = 1
    while destination.exists():
        destination = PROCESSED_BOOKS_DIR / f"{pdf_path.stem}_{counter}{pdf_path.suffix}"
        counter += 1

    shutil.move(str(pdf_path), str(destination))
    logger.info(f"✅ Moved {pdf_path.name} → processed_books/{destination.name}")
    return destination


def get_queue_status() -> dict:
    """
    Return a summary of the queue state.
    """
    pending = list(BOOKS_QUEUE_DIR.glob("*.pdf"))
    processed = list(PROCESSED_BOOKS_DIR.glob("*.pdf"))
    return {
        "pending_count": len(pending),
        "processed_count": len(processed),
        "pending_books": [p.name for p in sorted(pending)],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    status = get_queue_status()
    print(f"Queue status: {status['pending_count']} pending, {status['processed_count']} processed")
    for name in status["pending_books"]:
        print(f"  • {name}")
