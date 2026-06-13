from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_URL = "https://www.nseindia.com/option-chain"
HOME_URL = "https://www.nseindia.com/"


def launch_browser_with_fallback(playwright, headless: bool):
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
    ]

    launch_attempts = [
        ("msedge", {"channel": "msedge", "headless": headless, "args": launch_args}),
        ("chrome", {"channel": "chrome", "headless": headless, "args": launch_args}),
        ("chromium", {"headless": headless, "args": launch_args}),
    ]

    launch_errors = []
    for name, launch_kwargs in launch_attempts:
        try:
            print(f"Trying browser launch via: {name}")
            return playwright.chromium.launch(**launch_kwargs)
        except PlaywrightError as ex:
            launch_errors.append(f"{name}: {ex}")

    error_details = "\n\n".join(launch_errors)
    raise RuntimeError(
        "Could not launch any supported browser (chrome, msedge, chromium).\n"
        "If chromium download is blocked by TLS/corporate certificate policy, keep Chrome or Edge installed and retry.\n\n"
        f"Launch errors:\n{error_details}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Launch the NSE option chain page, keep the session open for a fixed duration, "
            "refresh every interval, and save full-page screenshots with timestamps."
        )
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Page URL to capture.")
    parser.add_argument(
        "--session-minutes",
        type=int,
        default=10,
        help="How long the browser session should stay open.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=2,
        help="How often to refresh and capture the page.",
    )
    parser.add_argument(
        "--output-dir",
        default="screenshots",
        help="Base output folder for screenshot sessions.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without showing the browser window.",
    )
    return parser.parse_args()


def dismiss_common_banners(page) -> None:
    selectors = [
        "button:has-text('Accept')",
        "button:has-text('I Accept')",
        "button:has-text('OK')",
        "button:has-text('Close')",
        "button[aria-label='close']",
    ]
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=1500)
            return
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue


def wait_for_option_chain_table(page, max_attempts: int = 5) -> None:
    for attempt in range(1, max_attempts + 1):
        page.wait_for_timeout(3000)
        dismiss_common_banners(page)

        has_rows = page.evaluate(
            """
            () => {
                const table = document.querySelector('#optionChainTable-indices');
                if (!table) return false;
                const rows = table.querySelectorAll('tbody tr');
                if (!rows || rows.length === 0) return false;
                const text = (table.innerText || '').toLowerCase();
                if (text.includes('no data')) return false;
                return true;
            }
            """
        )

        if has_rows:
            return

        print(f"Option-chain table not ready (attempt {attempt}/{max_attempts}), retrying...")
        if attempt < max_attempts:
            page.reload(wait_until="domcontentloaded", timeout=120000)

    raise RuntimeError(
        "NSE option-chain table rows did not load after multiple retries. "
        "This is typically due to transient NSE anti-bot/CDN behavior or missing initial session cookies."
    )


def open_nse_option_chain(page, url: str) -> None:
    # Prime NSE cookies/session first; direct deep-linking is less reliable for data widgets.
    page.goto(HOME_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(3000)
    dismiss_common_banners(page)

    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(3000)
    dismiss_common_banners(page)
    wait_for_option_chain_table(page)


def capture_session(url: str, session_minutes: int, interval_minutes: int, output_dir: str, headless: bool) -> None:
    if session_minutes <= 0:
        raise ValueError("session_minutes must be greater than 0")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be greater than 0")

    session_root = Path(output_dir)
    session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir = session_root / session_name
    session_dir.mkdir(parents=True, exist_ok=True)

    total_seconds = session_minutes * 60
    interval_seconds = interval_minutes * 60

    capture_offsets = list(range(0, total_seconds + 1, interval_seconds))
    if capture_offsets[-1] != total_seconds:
        capture_offsets.append(total_seconds)

    with sync_playwright() as playwright:
        browser = launch_browser_with_fallback(playwright, headless=headless)
        context = browser.new_context(
            viewport={"width": 1600, "height": 3200},
            locale="en-US",
            timezone_id="Asia/Kolkata",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            """
        )
        page = context.new_page()

        session_start = time.monotonic()

        try:
            open_nse_option_chain(page, url)

            for index, offset_seconds in enumerate(capture_offsets, start=1):
                now = time.monotonic()
                target_time = session_start + offset_seconds
                sleep_for = target_time - now
                if sleep_for > 0:
                    time.sleep(sleep_for)

                if index > 1:
                    page.reload(wait_until="domcontentloaded", timeout=120000)
                    page.wait_for_timeout(3000)
                    dismiss_common_banners(page)
                    wait_for_option_chain_table(page)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = session_dir / f"option_chain_{timestamp}.png"
                page.screenshot(path=str(file_path), full_page=True)
                print(f"Saved screenshot: {file_path}")
        finally:
            context.close()
            browser.close()

    print(f"Capture complete. Screenshots saved in: {session_dir.resolve()}")


def main() -> None:
    args = parse_args()
    capture_session(
        url=args.url,
        session_minutes=args.session_minutes,
        interval_minutes=args.interval_minutes,
        output_dir=args.output_dir,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
