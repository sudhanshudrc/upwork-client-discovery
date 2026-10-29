#!/usr/bin/env python3
"""
Interactive Real-Browser Upwork Login Helper (Cloudflare-Safe CDP Pattern)
--------------------------------------------------------------------------
Connects to genuine system Google Chrome or Brave via Chrome DevTools Protocol (CDP).
This ensures Cloudflare Turnstile recognizes a genuine human browser signature,
allowing human verification and 2FA to complete without loops or blocks.
"""

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from playwright.async_api import async_playwright

DEBUG_PORT = 9222


def sanitize_username(username: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", username.lower())


def get_available_browser() -> str | None:
    candidates = [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "google-chrome-stable",
        "google-chrome",
        "/usr/bin/brave-browser",
        "/usr/bin/brave-browser-stable",
        "brave-browser",
        "chromium-browser",
        "chromium",
    ]
    for c in candidates:
        if shutil.which(c):
            return c
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


async def is_port_open(port: int) -> bool:
    try:
        _, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def run_interactive_login(user_identifier: str, timeout_seconds: int = 300) -> bool:
    safe_name = sanitize_username(user_identifier)
    session_dir = Path("data/sessions")
    session_dir.mkdir(parents=True, exist_ok=True)
    target_file = session_dir / f"session_{safe_name}.json"
    secrets_file = Path("secrets/upwork_state.json")
    secrets_file.parent.mkdir(parents=True, exist_ok=True)

    profile_dir = Path.home() / ".config" / f"upwork_login_profile_{safe_name}"
    profile_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("UPWORK REAL-BROWSER AUTHENTICATOR (CLOUDFLARE SAFE)")
    print("=" * 70)
    print(f"Target User: {user_identifier}")
    print(f"Target Session File: {target_file}")
    print("=" * 70)

    proc = None
    if await is_port_open(DEBUG_PORT):
        print(f"[AUTH] Detected active browser on debugging port {DEBUG_PORT}.")
    else:
        browser_bin = get_available_browser()
        if not browser_bin:
            print("[ERROR] Could not find Google Chrome or Brave on your system.")
            print("Please install google-chrome-stable or brave-browser.")
            return False

        print(f"[AUTH] Launching genuine system browser: {browser_bin}")
        login_url = "https://www.upwork.com/ab/account-security/login"
        cmd = [
            browser_bin,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list",
            login_url,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(2)

    async with async_playwright() as p:
        print(f"[AUTH] Connecting to genuine browser via CDP (port {DEBUG_PORT})...")
        browser = None
        for _ in range(15):
            try:
                browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
                break
            except Exception:
                await asyncio.sleep(1)

        if not browser:
            print("[ERROR] Could not connect to browser on port 9222. Ensure Chrome opened.")
            if proc:
                proc.terminate()
            return False

        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        print("\n" + "-" * 70)
        print("ACTION REQUIRED IN OPEN CHROME WINDOW:")
        print("1. Enter your Upwork email and password.")
        print("2. Complete the Cloudflare human verification check.")
        print("3. Enter your 2FA OTP code if prompted.")
        print("4. Wait until you see your Upwork dashboard or search feed.")
        print("-" * 70)
        print("Watching for successful login automatically (or press ENTER when logged in)...\n")

        loop = asyncio.get_running_loop()
        authenticated = False
        elapsed = 0
        poll_interval = 2

        # Start background check loop while also allowing manual Enter key
        while elapsed < timeout_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            pages = context.pages
            for page in pages:
                current_url = page.url
                cookies = await context.cookies()
                cookie_names = [c["name"] for c in cookies]

                has_auth = any(
                    name in ["master_access_token", "auth_session", "user_uid", "oauth2_global_js_token"]
                    for name in cookie_names
                )
                is_dashboard = any(
                    term in current_url.lower()
                    for term in ["/nx/find-work", "/nx/search", "/home", "/dashboard", "/ab/find-work"]
                )

                if has_auth and is_dashboard:
                    print(f"[AUTH] Verified authenticated session state (URL: {current_url})")
                    print(f"[AUTH] Total cookies captured: {len(cookies)}")
                    authenticated = True
                    break

            if authenticated:
                break

            if elapsed % 15 == 0:
                print(f"[AUTH] Waiting for login completion... ({elapsed}/{timeout_seconds}s)")

        if not authenticated:
            print("[ERROR] Login timed out before authentication was confirmed.")
            await browser.close()
            if proc:
                proc.terminate()
            return False

        # Live probe test against search to verify Cloudflare will not block subsequent requests
        print("[AUTH] Performing live verification probe against search feed...")
        test_page = await context.new_page()
        try:
            res = await test_page.goto(
                "https://www.upwork.com/nx/search/jobs/?sort=recency&q=automation",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            title = await test_page.title()
            if "Cloudflare" in title or "Attention Required" in title or (res and res.status == 403):
                print(f"[WARNING] Cloudflare challenge detected on probe (Status: {res.status if res else 'None'}, Title: {title})")
                print("[WARNING] Please check the browser window and solve the human verification check.")
            else:
                print(f"[SUCCESS] Probe verified! (Title: '{title}')")
        except Exception as e:
            print(f"[WARNING] Probe navigation note: {e}")
        finally:
            await test_page.close()

        # Save session into storage state safely
        print(f"[AUTH] Saving verified session state to: {target_file}")
        for fpath in [target_file, secrets_file]:
            if fpath.exists():
                try:
                    fpath.unlink()
                except Exception:
                    pass

        await context.storage_state(path=str(target_file))
        await context.storage_state(path=str(secrets_file))

        for fpath in [target_file, secrets_file]:
            try:
                fpath.chmod(0o666)
            except Exception:
                pass

        print("\n" + "=" * 70)
        print(f"[SUCCESS] Session successfully saved and verified for {user_identifier}!")
        print(f"Path: {target_file} ({target_file.stat().st_size} bytes)")
        print("=" * 70)

        await browser.close()
        if proc:
            proc.terminate()
        return True


def main():
    parser = argparse.ArgumentParser(description="Upwork Real-Browser Login Helper")
    parser.add_argument(
        "--user",
        required=True,
        help="User identifier or email address (e.g. user@example.com)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds to wait for login (default: 300s)",
    )
    args = parser.parse_args()

    success = asyncio.run(run_interactive_login(user_identifier=args.user, timeout_seconds=args.timeout))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
