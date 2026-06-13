# NSE Option Chain Capture

Capture full-page screenshots of the NSE Option Chain page at fixed intervals during a session.

This script uses Playwright and includes reliability improvements for NSE:
- Browser fallback order: Edge -> Chrome -> Chromium
- Session priming via NSE homepage before opening option chain
- Retries until option-chain table rows are actually present
- Basic anti-automation fingerprint reduction

## Files

- [nse_option_chain_capture.py](nse_option_chain_capture.py): Main script
- [requirements.txt](requirements.txt): Python dependencies
- [screenshots](screenshots): Output directory for captured images

## Prerequisites

- Windows
- Python 3.13 (or compatible)
- Microsoft Edge or Google Chrome installed (recommended)

## Setup

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

3. Optional: install Playwright bundled browsers

```powershell
python -m playwright install
```

If browser download fails due to certificate issues, the script can still run by launching your locally installed Edge/Chrome.

## Run

Default run:

```powershell
python .\nse_option_chain_capture.py
```

Headless run:

```powershell
python .\nse_option_chain_capture.py --headless
```

Custom timings:

```powershell
python .\nse_option_chain_capture.py --session-minutes 30 --interval-minutes 5
```

## CLI Options

- --url: Target page URL (default: https://www.nseindia.com/option-chain)
- --session-minutes: Total session duration in minutes (default: 10)
- --interval-minutes: Refresh and capture interval in minutes (default: 2)
- --output-dir: Base output directory (default: screenshots)
- --headless: Run browser without UI

## Output

Each run creates a session folder under screenshots:

- screenshots/session_YYYYMMDD_HHMMSS/

Inside it, screenshots are saved as:

- option_chain_YYYYMMDD_HHMMSS.png

## How It Works

1. Launches browser with fallback strategy.
2. Opens NSE homepage first to establish session/cookies.
3. Navigates to option-chain page.
4. Waits until #optionChainTable-indices has tbody rows.
5. Captures full-page screenshots on schedule.

## Troubleshooting

### 1) playwright command not recognized

Use module invocation instead of standalone command:

```powershell
python -m playwright install
```

### 2) Browser executable missing

If Playwright Chromium is not installed, keep Edge or Chrome installed. The script tries those first.

### 3) TLS/certificate errors during Playwright download

Example: unable to get local issuer certificate

Workarounds:
- Use local Edge/Chrome (already supported by script)
- Ask your network/admin team to allow Playwright CDN certificate chain if bundled browsers are required

### 4) Option-chain table not visible in captures

The script already retries and validates table rows before capture. If NSE still returns partial UI:
- Retry after a short delay
- Run headed mode once (without --headless)
- Avoid very frequent refresh intervals

## Notes

- This project captures screenshots only. It does not parse or export table data.
- NSE page behavior can vary based on CDN, anti-bot checks, and network conditions.
