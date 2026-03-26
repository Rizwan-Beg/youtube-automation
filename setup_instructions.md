# Setup Instructions — YouTube Auto Factory

Complete setup guide for macOS with Python 3.11.

---

## Prerequisites

- **macOS** (tested on macOS 13+)
- **Python 3.11+** (check: `python3 --version`)
- **Homebrew** (check: `brew --version`)
- **Google Account** (for NotebookLM and YouTube)

---

## Step 1: Clone / Navigate to Project

```bash
cd /Users/rizwan/Devlopment/youtube\ automation/youtube_auto_factory
```

---

## Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Install Playwright Browser

```bash
playwright install chromium
```

---

## Step 5: Install FFmpeg

```bash
brew install ffmpeg
```

Verify: `ffmpeg -version`

---

## Step 6: Install Ollama + Llama3

```bash
# Install Ollama
brew install ollama

# Start Ollama server (keep running in background)
ollama serve &

# Pull the Llama3 model
ollama pull llama3
```

Verify: `ollama list` should show `llama3`.

---

## Step 7: Set Up Google Cloud Credentials

### YouTube Data API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **YouTube Data API v3**:
   - APIs & Services → Library → Search "YouTube Data API v3" → Enable
4. Create OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth Client ID
   - Application type: **Desktop app**
   - Download the JSON file
5. Rename the downloaded file to `client_secret.json`
6. Place it in the project root: `youtube_auto_factory/client_secret.json`

### First-Time OAuth

On the first run, a browser window will open asking you to authorize the app. After granting permission, a `token.json` file is created and reused for all future runs.

---

## Step 8: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
- `SCHEDULE_TIME` — when the daily pipeline runs (default: `10:00`)
- `YOUTUBE_CATEGORY_ID` — your preferred category (default: `27` = Education)
- `DRY_RUN=true` — for testing without NotebookLM/YouTube

---

## Step 9: First-Time NotebookLM Login

The bot uses a persistent browser profile. On the first run:

1. Run: `python -m scripts.main_pipeline`
2. A Chromium window opens showing NotebookLM
3. **Log in with your Google account manually**
4. The bot saves cookies and won't ask again

---

## Step 10: Add Books to Queue

Drop PDF files into `books_queue/`:

```bash
cp ~/Downloads/my_book.pdf books_queue/
```

---

## Step 11: Run the Pipeline

### One-time run:
```bash
python -m scripts.main_pipeline
```

### Daily scheduler:
```bash
python -m scripts.scheduler
```

### Cron job (alternative):
```bash
crontab -e
# Add:
0 10 * * * cd /path/to/youtube_auto_factory && /path/to/venv/bin/python -m scripts.main_pipeline >> logs/cron.log 2>&1
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `FFmpeg not found` | Run `brew install ffmpeg` |
| `Ollama connection refused` | Run `ollama serve` in a terminal |
| `OAuth error` | Delete `token.json` and re-run for fresh auth |
| `NotebookLM login required` | Delete `.browser_data/` folder and re-login |
| `Playwright timeout` | Increase `NOTEBOOKLM_TIMEOUT` in `.env` |
| `Thumbnail font issues` | Install Arial via Font Book or adjust font paths |

---

## File Safety

The following files contain secrets — **never commit them**:
- `client_secret.json`
- `token.json`
- `.env`

These are already in `.gitignore`.
