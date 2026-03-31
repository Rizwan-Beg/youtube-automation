"""
youtube_uploader.py — YouTube Data API v3 Upload

Handles OAuth2 authentication and video upload to YouTube,
including setting title, description, tags, category, privacy,
and custom thumbnail.
"""

import logging
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from scripts.config import (
    GOOGLE_CLIENT_SECRET_FILE,
    YOUTUBE_TOKEN_FILE,
    YOUTUBE_CATEGORY_ID,
    DRY_RUN,
)

logger = logging.getLogger(__name__)

# YouTube API scope for video upload and thumbnail setting
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# Maximum number of upload retries
MAX_RETRIES = 3


def _get_authenticated_service():
    """
    Authenticate with YouTube Data API v3 using OAuth2.

    On first run, opens a browser for user consent.
    On subsequent runs, uses the cached token.json.

    Returns:
        Google API service object for YouTube.
    """
    creds = None

    # Load existing token
    token_path = Path(YOUTUBE_TOKEN_FILE)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("🔄 Refreshing expired YouTube token...")
            creds.refresh(Request())
        else:
            logger.info("🔐 Starting YouTube OAuth flow (browser will open)...")
            if not Path(GOOGLE_CLIENT_SECRET_FILE).exists():
                raise FileNotFoundError(
                    f"OAuth client secret file not found: {GOOGLE_CLIENT_SECRET_FILE}\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080, open_browser=True)

        # Save token for next run
        with open(str(token_path), "w") as f:
            f.write(creds.to_json())
        logger.info(f"💾 Token saved: {token_path}")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: Path = None,
    privacy: str = "public",
) -> str:
    """
    Upload a video to YouTube with metadata and optional thumbnail.

    Args:
        video_path:      Path to the MP4 video file.
        title:           Video title.
        description:     Video description.
        tags:            List of tags.
        thumbnail_path:  Path to thumbnail PNG (optional).
        privacy:         Privacy status: 'public', 'unlisted', 'private'.

    Returns:
        YouTube video ID of the uploaded video.

    Raises:
        FileNotFoundError: If video file doesn't exist.
        HttpError: If YouTube API returns an error.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if DRY_RUN:
        logger.info("🏜️  DRY RUN — Skipping YouTube upload.")
        logger.info(f"   Title: {title}")
        logger.info(f"   Video: {video_path.name}")
        return "DRYRUN_VIDEO_ID"

    youtube = _get_authenticated_service()

    # ------------------------------------------------------------------
    # Build video metadata
    # ------------------------------------------------------------------
    body = {
        "snippet": {
            "title": title[:100],  # YouTube title limit
            "description": description[:5000],  # YouTube description limit
            "tags": tags[:500] if tags else [],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # ------------------------------------------------------------------
    # Upload video
    # ------------------------------------------------------------------
    logger.info(f"📤 Uploading to YouTube: {title}")
    logger.info(f"   File: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=256 * 1024,  # 256KB chunks for progress reporting
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    # Execute with progress tracking
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            logger.info(f"   Upload progress: {progress}%")

    video_id = response["id"]
    logger.info(f"✅ Video uploaded! ID: {video_id}")
    logger.info(f"   URL: https://www.youtube.com/watch?v={video_id}")

    # ------------------------------------------------------------------
    # Set custom thumbnail (if provided)
    # ------------------------------------------------------------------
    if thumbnail_path and thumbnail_path.exists():
        _set_thumbnail(youtube, video_id, thumbnail_path)

    return video_id


def _set_thumbnail(youtube, video_id: str, thumbnail_path: Path) -> None:
    """
    Set a custom thumbnail for an uploaded video.
    """
    try:
        logger.info(f"🖼️  Setting custom thumbnail: {thumbnail_path.name}")
        media = MediaFileUpload(str(thumbnail_path), mimetype="image/png")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=media,
        ).execute()
        logger.info("✅ Thumbnail set successfully.")
    except HttpError as e:
        # Thumbnail setting may fail if channel isn't verified
        logger.warning(
            f"⚠️  Could not set thumbnail (may require channel verification): {e}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("YouTube uploader module loaded.")
    print("Run _get_authenticated_service() to test OAuth.")
