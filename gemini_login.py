import time
from playwright.sync_api import sync_playwright

# Path to the shared browser profile
USER_DATA_DIR = ".browser_data"

print("========================================")
print("     Gemini Manual Login Setup          ")
print("========================================")
print("1. A Chromium browser window will open shortly.")
print("2. Navigate the initial welcome screens for Gemini.")
print("3. Accept any Terms of Service or 'I agree' buttons.")
print("4. Once you see the normal chat prompt box,")
print("   head back to this terminal and press Ctrl+C to save.")
print("========================================")
print("Opening browser in 3 seconds...")
time.sleep(3)

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        channel="chrome",
        headless=False,
    )
    page = context.new_page()
    page.goto("https://gemini.google.com/app")
    
    print("\nBrowser is open! Please clear the welcome screens.")
    print("Press Ctrl+C here in the terminal when you are fully logged in and see the chat box.")
    
    try:
        # Keep the browser open indefinitely until the user manually stops
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSaving session and closing browser...")
        context.close()
        print("Done!")
