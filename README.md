# YouTube Auto Factory

> Fully automated YouTube video production pipeline — one video per day from a queue of PDF books.

## Architecture

```
PDF Queue → NotebookLM Bot → Video Download → Watermark Removal
    → Thumbnail Generation → Metadata (LLM) → YouTube Upload
```

## Quick Start

```bash
# 1. Install dependencies
cd youtube_auto_factory
pip install -r requirements.txt
playwright install chromium
brew install ffmpeg
ollama pull llama3

# 2. Configure
cp .env.example .env
# Edit .env with your settings

# 3. Add Google OAuth credentials
# Place client_secret.json in project root
# (Download from Google Cloud Console)

# 4. Drop PDFs into books_queue/

# 5. Run once
python3 -m scripts.main_pipeline

# 6. Run on schedule (daily)
python3 -m scripts.scheduler
```

## Project Structure

```
youtube_auto_factory/
├── books_queue/          # Drop PDF books here
├── processed_books/      # Completed PDFs moved here
├── videos_raw/           # Raw downloads from NotebookLM
├── videos_clean/         # Watermark-removed final videos
├── thumbnails/           # Generated YouTube thumbnails
├── metadata/             # JSON metadata per book
├── logs/                 # Pipeline log files
├── scripts/
│   ├── config.py                # Centralised configuration
│   ├── queue_manager.py         # PDF queue management
│   ├── notebooklm_bot.py        # NotebookLM browser automation
│   ├── video_downloader.py      # Download handler
│   ├── watermark_remover.py     # FFmpeg delogo filter
│   ├── thumbnail_generator.py   # Pillow thumbnail creator
│   ├── metadata_generator.py    # Ollama/Llama3 metadata
│   ├── youtube_uploader.py      # YouTube API v3 upload
│   ├── main_pipeline.py         # Pipeline orchestrator
│   └── scheduler.py             # Daily scheduler
├── .env.example
├── requirements.txt
└── README.md
```

## Configuration

All settings are in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CLIENT_SECRET_FILE` | `client_secret.json` | OAuth client secret path |
| `YOUTUBE_CATEGORY_ID` | `27` (Education) | YouTube video category |
| `OLLAMA_MODEL` | `llama3` | Local LLM for metadata |
| `SCHEDULE_TIME` | `10:00` | Daily run time (24h) |
| `DRY_RUN` | `false` | Skip NotebookLM & YouTube |
| `NOTEBOOKLM_MAX_RETRIES` | `3` | Retry attempts |
| `NOTEBOOKLM_TIMEOUT` | `900` | Generation timeout (sec) |
| `DELOGO_X/Y/W/H` | `1100/620/170/80` | Watermark region |

## Running as Cron Job

```bash
# Edit crontab
crontab -e

# Run daily at 10:00 AM
0 10 * * * cd /path/to/youtube_auto_factory && /path/to/python -m scripts.main_pipeline >> logs/cron.log 2>&1
```

## DRY RUN Mode

Set `DRY_RUN=true` in `.env` to test the pipeline without:
- NotebookLM automation
- YouTube upload

All other steps (thumbnail, metadata, watermark) will still execute.

## Logs

All pipeline activity is logged to:
- **Console** — real-time progress
- **`logs/pipeline.log`** — persistent log file

## License

MIT
