# Setup Instructions — YouTube Auto Factory

Complete setup guide for macOS with Python 3.11.

---

## Prerequisites

- **macOS** (tested on macOS 13+)
- **Python 3.11+** (check: `python3 --version`)
- **Homebrew** (check: `brew --version`)
- **Google Account** (for NotebookLM and YouTube)
- **Google AI Studio Account** (for Gemini API thumbnails)

---

## Step 1: Clone / Navigate to Project

```bash
cd "/Users/rizwan/Devlopment/youtube automation/youtube_auto_factory"
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

*(Note: The NotebookLM bot uses your system's Google Chrome, but Playwright requires this base installation.)*

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

# Start Ollama server (keep running in a separate terminal tab)
ollama serve

# Pull the Llama3 model (in another tab)
ollama pull llama3
```

Verify: `ollama list` should show `llama3`.

---

## Step 7: Set Up API Credentials

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

*(On the first pipeline run, a browser will ask you to authorize your YouTube account, generating `token.json`)*

### Gemini API (for Thumbnails)
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create an API Key in a project with billing enabled (required for `gemini-3.1-flash-image-preview` generation).
3. Copy the key to your `.env` file (see Step 8).

---

## Step 8: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
- `GEMINI_API_KEY` — Your AI Studio key for thumbnail generation
- `SCHEDULE_TIME` — when the daily pipeline runs (default: `10:00` if using scheduler.py)
- `YOUTUBE_CATEGORY_ID` — your preferred category (default: `27` = Education)
- `DRY_RUN=true` — for testing without making real uploads

---

## Step 9: First-Time NotebookLM Login

The bot uses a persistent browser profile. Before automation can work:

1. Run: `python3 -m scripts.main_pipeline`
2. A Chromium window opens showing NotebookLM
3. **Log in with your Google account manually**
4. The bot saves cookies to `.browser_data/` and won't ask again next time

---

## Step 10: Add Topics to Queue

Instead of uploading PDFs, the pipeline is now topic-and-description driven.
Add your video ideas directly into `topics.json`:

```json
{
  "topics": [
    {
      "title": "The Machine Learning Landscape | All about ML in 10 Minutes",
      "description": "Explain machine learning using references from the O'Reilly book. Keep it under 10 minutes and engaging."
    }
  ]
}
```
*Note: After a video is generated and uploaded successfully, the pipeline automatically removes it from `topics.json` and saves it to `processed_topics.json`.*

---

## Step 11: Run the Pipeline

### Option A: One-time manual run
```bash
python3 -m scripts.main_pipeline
```
*(Optionally run `python3 process_existing.py` to regenerate thumbnails/metadata for already downloaded raw videos)*

### Option B: Automated Daily Uploads (Cron Job)
The system is built to silently run in the background. If you set this up, your Mac will check every 10 minutes (between 9:30 PM and 11:50 PM) and upload exactly 1 video per day from your queue.

1. Open your terminal and type: `crontab -e`
2. Press `i` to enter Insert Mode (if in vim).
3. Paste:
```bash
*/20 * * * * cd "/Users/rizwan/Devlopment/youtube automation/youtube_auto_factory" && /opt/homebrew/bin/python3 -m scripts.cron_runner >> logs/cron.log 2>&1
```
4. Save and exit (press `Esc`, type `:wq`, drop `Enter`).

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `FFmpeg not found` | Run `brew install ffmpeg` |
| `Ollama connection refused` | Run `ollama serve` in a terminal |
| `Gemini API fail` | Check `GEMINI_API_KEY` in `.env` or billing status in AI Studio |
| `OAuth error` | Delete `token.json` and re-run for fresh YouTube auth |
| `NotebookLM login / crash` | Delete `.browser_data/` folder and re-login manually |

---

## File Safety

The following files contain secrets — **never commit them**:
- `client_secret.json`
- `token.json`
- `.env`

*(These are correctly ignored by `.gitignore`)*
