"""
notebooklm_bot.py — NotebookLM Browser Automation (Topic-based)

Uses Playwright to:
1. Open NotebookLM in a persistent Chromium session
2. Create a new notebook
3. Type a scriptwriter prompt into the chat (topic-based, no PDF upload)
4. Click "Video Overview" in the Studio panel to generate a video
5. Wait for video generation to complete
6. Download the resulting video

NOTE: NotebookLM has no public API — this bot automates the web UI.
      UI selectors may need updating if Google changes the interface.
"""

import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from scripts.config import (
    BROWSER_DATA_DIR,
    VIDEOS_RAW_DIR,
    NOTEBOOKLM_MAX_RETRIES,
    NOTEBOOKLM_TIMEOUT,
    DRY_RUN,
)

logger = logging.getLogger(__name__)

# The prompt template sent to NotebookLM — {topic} and {description} are replaced at runtime
VIDEO_PROMPT_TEMPLATE = """You are a professional YouTube scriptwriter.

Create a highly engaging, cinematic video script (6–8 minutes) on:

"{topic}"

Additional context and guidance for this video:
{description}

Requirements:

Start with a strong hook in first 5 seconds
Make intresting videos 
Use storytelling style
Keep global audience
Add visual suggestions for each scene

Make it feel like a viral YouTube video. Do FastResearch and All just start the video making"""

NOTEBOOKLM_URL = "https://notebooklm.google.com/"


def generate_from_topic(topic_title: str, safe_name: str, description: str = "") -> Path:
    """
    Full automation flow: create notebook, type prompt, generate video, download it.

    Args:
        topic_title: The topic string (e.g. "Saving $10 Daily Looks Useless...").
        safe_name:   Sanitized name (used for output filename).
        description: Additional context/guidance for video generation.

    Returns:
        Path to the downloaded raw video file.

    Raises:
        RuntimeError: If video generation or download fails after all retries.
    """
    if DRY_RUN:
        logger.info("🏜️  DRY RUN — Skipping NotebookLM automation.")
        placeholder = VIDEOS_RAW_DIR / f"{safe_name}_raw.mp4"
        placeholder.write_bytes(b"DRYRUN_PLACEHOLDER")
        return placeholder

    output_path = VIDEOS_RAW_DIR / f"{safe_name}_raw.mp4"

    for attempt in range(1, NOTEBOOKLM_MAX_RETRIES + 1):
        logger.info(f"🔄 NotebookLM attempt {attempt}/{NOTEBOOKLM_MAX_RETRIES}")
        try:
            _run_automation(topic_title, safe_name, output_path, description)
            logger.info(f"✅ Video downloaded: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"❌ Attempt {attempt} failed: {e}")
            if attempt == NOTEBOOKLM_MAX_RETRIES:
                raise RuntimeError(
                    f"NotebookLM automation failed after {NOTEBOOKLM_MAX_RETRIES} attempts."
                ) from e
            logger.info("⏳ Waiting 30s before retrying...")
            time.sleep(30)

    raise RuntimeError("Unexpected exit from retry loop.")


# =========================================================================
#  MAIN AUTOMATION FLOW
# =========================================================================

def _run_automation(topic_title: str, safe_name: str, output_path: Path, description: str = "") -> None:
    """
    Internal: run one full attempt of the NotebookLM automation.

    Flow (topic-based — no PDF upload):
      1. Navigate to notebooklm.google.com  → home page
      2. Click "+ Create new" button          → opens new empty notebook
      3. Close any source upload modal        → stay in empty notebook
      4. Type scriptwriter prompt in chat     → includes the topic + description
      5. Submit prompt and wait for response
      6. Click "Video Overview" in Studio     → video generation starts
      7. Wait for video to be ready
      8. Download the video via 3-dot menu
    """
    prompt = VIDEO_PROMPT_TEMPLATE.format(topic=topic_title, description=description or "No additional context provided.")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-extensions",
            ],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_navigation_timeout(180_000)
        page.set_default_timeout(120_000)

        try:
            # ==============================================================
            # STEP 1: Navigate to NotebookLM home page
            # ==============================================================
            logger.info("🌐 Step 1 — Navigating to NotebookLM...")
            page.goto(NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=180_000)
            logger.info("⏳ Waiting for NotebookLM UI to fully load...")
            page.wait_for_selector('button:has-text("Create new")', timeout=120000)
            _wait_for_page_stable(page, 5)
            _debug_screenshot(page, "01_home_page")

            if _needs_login(page):
                logger.warning(
                    "⚠️  Google sign-in required. Please log in manually in the "
                    "browser window. The bot will wait up to 5 minutes."
                )
                page.wait_for_url("**/notebooklm.google.com/**", timeout=300_000)
                _wait_for_page_stable(page, 5)

            # ==============================================================
            # STEP 2: Click "+ Create new" button
            # ==============================================================
            logger.info("📓 Step 2 — Creating new notebook...")
            _find_and_click(page, [
                'button:has-text("Create new")',
                'button:has-text("Create notebook")',
                'text="Create new notebook"',
                'button:has-text("+ Create new")',
                '[aria-label*="Create new" i]',
                '[aria-label*="Create notebook" i]',
                'button:has-text("New")',
            ], step_name="Create new notebook")

            _wait_for_page_stable(page, 4)
            _debug_screenshot(page, "02_new_notebook")

            # ==============================================================
            # STEP 3: Close the source upload modal (we don't need it)
            # ==============================================================
            logger.info("🔄 Step 3 — Closing source modal if open...")
            _debug_screenshot(page, "03_before_close_modal")

            modal_closed = False
            # From screenshot: modal has a clear X button in top-right
            close_selectors = [
                # The X button on the "Create Audio and Video Overviews" modal
                'button[aria-label="Close" i]',
                'button[aria-label="close" i]',
                'button[aria-label="Close dialog" i]',
                '[aria-label="Close" i]',
                'button:has-text("×")',
                'button:has-text("✕")',
                'button.close-button',
                # Material close icon button
                'button:has(mat-icon:has-text("close"))',
            ]
            for sel in close_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        modal_closed = True
                        logger.info(f"   Closed modal via: {sel}")
                        break
                except Exception:
                    continue

            if not modal_closed:
                # Fallback: press Escape to close any overlay
                logger.info("   No close button found, pressing Escape")
                page.keyboard.press("Escape")
                time.sleep(1)
                page.keyboard.press("Escape")

            _wait_for_page_stable(page, 3)
            _debug_screenshot(page, "03_after_close_modal")

            # ==============================================================
            # STEP 4: Enter the scriptwriter prompt in chat
            # ==============================================================
            logger.info(f"💬 Step 4 — Entering prompt for topic: {topic_title[:50]}...")
            _debug_screenshot(page, "04_before_prompt")

            # From screenshot: the chat input is at the bottom with
            # placeholder "Start typing..." and an arrow (→) send button
            prompt_input = _find_element(page, [
                'input[placeholder*="Start typing"]',
                'textarea[placeholder*="Start typing"]',
                '[contenteditable="true"]',
                'input[type="text"]',
                'textarea',
            ], step_name="Chat input")

            prompt_input.click()
            time.sleep(0.3)

            # Use clipboard to paste the full prompt instantly.
            # This works with contenteditable divs (React/Angular SPAs)
            # where setting .value via JS won't trigger framework state.
            page.evaluate(
                """async (text) => {
                    await navigator.clipboard.writeText(text);
                }""",
                prompt
            )
            time.sleep(0.2)
            page.keyboard.press("Meta+v")  # Paste on Mac

            time.sleep(0.5)
            _debug_screenshot(page, "04_prompt_filled")
            logger.info(f"   Prompt pasted ({len(prompt)} chars)")

            # ==============================================================
            # STEP 5: Submit prompt and wait for AI + Fast Research
            # ==============================================================
            logger.info("🚀 Step 5 — Submitting prompt...")

            _submit_chat(page)
            time.sleep(1)

            logger.info("⏳ Waiting for AI to respond in the chat...")
            _wait_for_chat_response(page, timeout=120)
            _debug_screenshot(page, "05_chat_response")
            logger.info("✅ AI responded in chat")

            # ==============================================================
            # STEP 5b: Wait for Fast Research & import sources
            # ==============================================================
            logger.info("🔍 Step 5b — Waiting for Fast Research to complete...")

            # From screenshot: Fast Research runs automatically after the
            # prompt. It shows "Fast Research completed!" with research
            # results and a green "+ Import" button. We MUST click Import
            # to add sources to the notebook before generating video.
            _wait_for_fast_research(page, timeout=90)
            _debug_screenshot(page, "05b_fast_research_done")

            # Click "+ Import" to add the research sources
            logger.info("📥 Importing Fast Research sources...")
            import_clicked = False
            import_selectors = [
                'button:has-text("Import")',
                'button:has-text("+ Import")',
                '[aria-label*="Import" i]',
                'text="Import"',
                'text="+ Import"',
            ]
            for sel in import_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=5000):
                        btn.click()
                        import_clicked = True
                        logger.info(f"   Clicked Import via: {sel}")
                        break
                except Exception:
                    continue

            if not import_clicked:
                logger.warning("⚠️  Could not find Import button — continuing anyway")
            else:
                # Wait for sources to be imported into the notebook
                logger.info("⏳ Waiting for sources to be imported...")
                time.sleep(10)
                _wait_for_page_stable(page, 5)

            _debug_screenshot(page, "05b_after_import")

            # ==============================================================
            # STEP 5c: Send follow-up prompt to start video creation
            # ==============================================================
            logger.info("🎬 Step 5c — Sending follow-up prompt to start video...")

            follow_up = "Now create a explainer video based on these sources. Start the video making."

            # Click the chat input again
            prompt_input2 = _find_element(page, [
                'input[placeholder*="Start typing"]',
                'textarea[placeholder*="Start typing"]',
                '[contenteditable="true"]',
                'input[type="text"]',
                'textarea',
            ], step_name="Chat input (follow-up)")

            prompt_input2.click()
            time.sleep(0.3)

            # Paste the follow-up prompt
            page.evaluate(
                """async (text) => {
                    await navigator.clipboard.writeText(text);
                }""",
                follow_up
            )
            time.sleep(0.2)
            page.keyboard.press("Meta+v")  # Paste on Mac
            time.sleep(0.3)

            _submit_chat(page)

            logger.info("⏳ Waiting for AI to respond to follow-up...")
            _wait_for_chat_response(page, timeout=120)
            _debug_screenshot(page, "05c_followup_response")
            logger.info("✅ Follow-up response received")

            # ==============================================================
            # STEP 6: Click "Video Overview" in Studio panel
            # ==============================================================
            logger.info("🎬 Step 6 — Clicking 'Video Overview' in Studio panel...")
            _debug_screenshot(page, "06_before_video_overview")

            _find_and_click(page, [
                'text="Video Overview"',
                'button:has-text("Video Overview")',
                '[aria-label*="Video Overview" i]',
                'text="Video overview"',
                'button:has-text("Video overview")',
                'text="Video"',
            ], step_name="Video Overview")

            _wait_for_page_stable(page, 3)
            _debug_screenshot(page, "06_after_video_overview_click")

            # Confirm generation if a dialog appears
            try:
                confirm_btns = [
                    'button:has-text("Generate")',
                    'button:has-text("Create")',
                    'button:has-text("Start")',
                    'button:has-text("OK")',
                    'button:has-text("Confirm")',
                ]
                for sel in confirm_btns:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=5000):
                            btn.click()
                            logger.info(f"   Confirmed generation via: {sel}")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            logger.info("🚀 Video generation started. Waiting for completion...")

            # ==============================================================
            # STEP 7: Wait for video generation to complete
            # ==============================================================
            _wait_for_video_generation(page)
            _debug_screenshot(page, "07_video_ready")

            # ==============================================================
            # STEP 8: Download the video via 3-dot menu
            # ==============================================================
            logger.info("⬇️  Step 8 — Downloading video via 3-dot menu...")
            _debug_screenshot(page, "08_before_download")

            three_dot_selectors = [
                'button[aria-label*="More" i]',
                'button[aria-label*="more options" i]',
                'button[aria-label*="menu" i]',
                'button:has-text("⋮")',
                'button:has-text("…")',
                '[aria-label*="options" i]',
                'button.more-button',
                '[data-testid*="more" i]',
                'button:has(mat-icon)',
                'button.mat-icon-button',
            ]

            three_dot_clicked = False
            try:
                for sel in three_dot_selectors:
                    try:
                        buttons = page.locator(sel)
                        count = buttons.count()
                        if count > 0:
                            buttons.nth(count - 1).click()
                            three_dot_clicked = True
                            logger.info(
                                f"   Clicked 3-dot menu via: {sel} "
                                f"(button {count}/{count})"
                            )
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            if not three_dot_clicked:
                _debug_screenshot(page, "08_no_three_dot")
                raise RuntimeError(
                    "Could not find 3-dot menu (⋮) button in Studio panel."
                )

            _wait_for_page_stable(page, 2)
            _debug_screenshot(page, "08_dropdown_open")

            # Click "Download" from the dropdown
            try:
                with page.expect_download(timeout=120_000) as download_info:
                    _find_and_click(page, [
                        'text="Download"',
                        '[role="menuitem"]:has-text("Download")',
                        'button:has-text("Download")',
                        'a:has-text("Download")',
                        '[aria-label*="Download" i]',
                    ], step_name="Download menu item")

                download = download_info.value
                download.save_as(str(output_path))
                logger.info(f"💾 Video saved: {output_path}")

            except Exception as e:
                _debug_screenshot(page, "08_download_failed")
                raise RuntimeError(f"Could not download video: {e}")

        except Exception:
            _debug_screenshot(page, "error_state")
            raise
        finally:
            context.close()


# =========================================================================
#  HELPER FUNCTIONS
# =========================================================================

def _submit_chat(page) -> None:
    """
    Click the send button (→ arrow) next to the chat input, or press Enter.
    """
    submitted = False
    send_selectors = [
        'button[aria-label*="Send" i]',
        'button[aria-label*="submit" i]',
        'button:has-text("→")',
    ]

    for sel in send_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                submitted = True
                logger.info(f"   Submitted via button: {sel}")
                break
        except Exception:
            continue

    # Fallback: press Enter
    if not submitted:
        logger.info("   Fallback: pressing Enter to submit")
        page.keyboard.press("Enter")


def _wait_for_fast_research(page, timeout: int = 90) -> None:
    """
    Wait for NotebookLM's Fast Research to complete.

    After a prompt is sent, NotebookLM may trigger Fast Research which
    searches the web for relevant sources. This shows up in the left panel
    as 'Fast Research completed!' with research results and an Import button.
    """
    start = time.time()
    poll_interval = 5

    while (time.time() - start) < timeout:
        # Check for "Fast Research completed!" indicator
        try:
            research_indicators = [
                'text="Fast Research completed!"',
                'text="Fast Research completed"',
                ':text("Fast Research completed")',
                'button:has-text("Import")',
                'button:has-text("+ Import")',
            ]
            for sel in research_indicators:
                if page.locator(sel).count() > 0:
                    logger.info("🔍 Fast Research completed!")
                    time.sleep(3)  # Let UI settle
                    return
        except Exception:
            pass

        elapsed = int(time.time() - start)
        logger.info(f"   ⏳ Waiting for Fast Research... ({elapsed}s / {timeout}s)")
        time.sleep(poll_interval)

    logger.warning(f"⚠️  Fast Research didn't complete in {timeout}s — continuing anyway")



def _find_and_click(page, selectors: list, step_name: str = "element"):
    """
    Try multiple selectors in order to find and click an element.
    Returns the locator that was clicked.
    Raises RuntimeError if none of the selectors matched.
    """
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=5000):
                logger.info(f"   Found '{step_name}' via: {selector}")
                locator.click()
                return locator
        except Exception:
            continue

    _debug_screenshot(page, f"not_found_{step_name.replace(' ', '_').lower()}")
    raise RuntimeError(
        f"Could not find '{step_name}'. "
        f"The NotebookLM UI may have changed — check debug screenshots in logs/."
    )


def _find_element(page, selectors: list, step_name: str = "element"):
    """
    Try multiple selectors in order to find a visible element (without clicking).
    Returns the locator.
    Raises RuntimeError if none of the selectors matched.
    """
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=5000):
                logger.info(f"   Found '{step_name}' via: {selector}")
                return locator
        except Exception:
            continue

    _debug_screenshot(page, f"not_found_{step_name.replace(' ', '_').lower()}")
    raise RuntimeError(
        f"Could not find '{step_name}'. "
        f"The NotebookLM UI may have changed — check debug screenshots in logs/."
    )


def _wait_for_page_stable(page, wait_seconds: int = 5) -> None:
    """Wait for the page to stabilise after navigation or interaction."""
    time.sleep(wait_seconds)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10_000)
    except PlaywrightTimeout:
        pass


def _needs_login(page) -> bool:
    """Check if the page is showing a Google sign-in prompt."""
    try:
        sign_in_selectors = [
            'text="Sign in"',
            'text="Sign In"',
            'button:has-text("Sign in")',
            '[data-identifier]',
        ]
        for selector in sign_in_selectors:
            if page.locator(selector).count() > 0:
                return True
        return False
    except Exception:
        return False


def _debug_screenshot(page, name: str) -> None:
    """Save a debug screenshot to the logs directory."""
    try:
        from scripts.config import LOGS_DIR
        screenshot_path = LOGS_DIR / f"debug_{name}_{int(time.time())}.png"
        page.screenshot(path=str(screenshot_path))
        logger.info(f"📸 Debug screenshot: {screenshot_path.name}")
    except Exception as e:
        logger.warning(f"⚠️  Could not save screenshot: {e}")


def _wait_for_chat_response(page, timeout: int = 120) -> None:
    """
    Wait for the AI to respond in the Chat panel.
    Looks for response indicators (text content appearing, loading spinners disappearing).
    """
    start = time.time()
    poll_interval = 5

    while (time.time() - start) < timeout:
        try:
            response_indicators = [
                'text="Save to note"',
                'button:has-text("Save to note")',
                '[aria-label*="thumbs" i]',
                '[aria-label*="Copy" i]',
            ]
            for sel in response_indicators:
                if page.locator(sel).count() > 0:
                    logger.info("   AI response detected in chat")
                    time.sleep(3)
                    return
        except Exception:
            pass

        elapsed = int(time.time() - start)
        logger.info(f"   ⏳ Waiting for AI response... ({elapsed}s / {timeout}s)")
        time.sleep(poll_interval)

    logger.warning(f"⚠️  Chat response timeout after {timeout}s — continuing anyway")


def _wait_for_video_generation(page, timeout: int = None) -> None:
    """
    Poll the page until video generation is complete or timeout is reached.
    """
    timeout = timeout or NOTEBOOKLM_TIMEOUT
    start = time.time()
    poll_interval = 15

    while (time.time() - start) < timeout:
        ready_selectors = [
            'button:has-text("Download")',
            'a:has-text("Download")',
            'button[aria-label*="download" i]',
            'video',
            'button:has-text("Play")',
            '[aria-label*="Play" i]',
        ]
        for sel in ready_selectors:
            try:
                if page.locator(sel).count() > 0:
                    logger.info("🎬 Video generation complete!")
                    time.sleep(3)
                    return
            except Exception:
                continue

        try:
            error_selectors = [
                'text="error"',
                'text="failed"',
                'text="unable"',
                'text="Error"',
                'text="Failed"',
            ]
            for sel in error_selectors:
                if page.locator(sel).count() > 0:
                    _debug_screenshot(page, "generation_error")
                    raise RuntimeError(
                        "NotebookLM reported an error during video generation."
                    )
        except RuntimeError:
            raise
        except Exception:
            pass

        elapsed = int(time.time() - start)
        logger.info(f"⏳ Waiting for video generation... ({elapsed}s / {timeout}s)")
        time.sleep(poll_interval)

    _debug_screenshot(page, "generation_timeout")
    raise TimeoutError(f"Video generation timed out after {timeout} seconds.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("NotebookLM bot module loaded. Use generate_from_topic() to run.")
