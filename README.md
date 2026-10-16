# Instagram Comments Scraper

Selenium-based scraper that exports the comments of an Instagram **post or reel** to an Excel file.

> Fork of [AgiMaulana/Instagram-Comments-Scraper](https://github.com/AgiMaulana/Instagram-Comments-Scraper) (MIT).
> Instagram changes its markup often, so selectors may need adjusting. They all live in `constants.py`.

## Features
- Works on posts (`/p/`), reels (`/reel/`) and the reels feed (`/reels/`)
- Persistent Chrome profile: log in (and enter the verification code) once, the session is reused afterwards
- Asks for the 2FA verification code in the terminal when Instagram requires it
- Closes "Save login info", notification and similar pop-ups
- Loads comments by scrolling, expands "View all N replies", optionally opens hidden comments
- Limits for rounds and number of comments, configurable pauses
- Output `.xlsx` with columns `name`, `comment`, `source_url` and `hidden`

## Requirements
- Python 3.10+
- Google Chrome (Selenium 4 downloads the matching driver automatically)

## Installation
1. Clone your copy of this repo
   ```bash
   git clone <your-fork-url>
   cd Instagram-Comments-Scraper
   ```
2. Create and activate a virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Configure credentials and settings
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `IG_USERNAME` and `IG_PASSWORD`. Use a dedicated scraping account rather than your main one.
   `.env` is git-ignored; the password is only used to fill the login form.

## Usage
```bash
python scraper.py
```
The script asks for:
1. the post/reel URL, e.g. `https://www.instagram.com/reel/XXXXXXXXXXX/`
2. the output file name (default `comments_<shortcode>`; `.xlsx` is added automatically)

On the first run a Chrome window opens and logs in. If Instagram asks for a verification code, type it in the terminal.
The session is stored in `.chrome-profile/`, so later runs skip login.

## Settings (`.env`)
| Variable | Default | Meaning |
|---|---|---|
| `IG_USERNAME`, `IG_PASSWORD` | – | Instagram login (only needed when not logged in) |
| `LOAD_COMMENT_CLICKS` | `10` | Max rounds of scroll / load more / expand replies |
| `MAX_COMMENTS` | `0` | Max comments to export, `0` = unlimited |
| `INCLUDE_HIDDEN_COMMENTS` | `1` | `1` = also open "View hidden comments" and add them (`hidden` column = `yes`) |
| `SLEEP_SCROLL_SECONDS` | `2` | Pause after each scroll round |
| `SLEEP_CLICK_SECONDS` | `0.5` | Pause between button clicks |
| `SLEEP_AFTER_LOGIN_SECONDS` | `2` | Pause after logging in |
| `WAIT_COMMENTS_SECONDS` | `6` | Max wait for comments after clicking the comment icon |

If comments load slowly and the run stops early, increase `SLEEP_SCROLL_SECONDS`.

## Project layout
| File | Purpose |
|---|---|
| `scraper.py` | Entrypoint: asks URL and file name, runs the scraper |
| `instagram_scraper.py` | `InstagramCommentScraper` class (login, pop-ups, open/load/extract comments, export) |
| `constants.py` | Selectors, XPaths, JS snippets, waits and env defaults |
| `config.py` | `ScraperConfig` dataclass, reads `.env` |
| `excel_exporter.py` | Writes the `.xlsx` file |

## Troubleshooting
- **No comments detected**: the script saves `debug_no_comments.png`, `debug_page.html` and `debug_state.json`
  (the last one only holds element counts). Compare against `constants.py` and adjust the selectors.
  These files contain page content, so do not commit or share them (they are git-ignored).
- **Wrong reel opened in the reels feed**: use the single reel URL (`/reel/<code>/`) instead of `/reels/<code>/`.
- **Hidden comments not found**: the label/XPath (`HIDDEN_COMMENTS_XPATH`) is untested against a live page; adjust it in `constants.py`.

## Disclaimer
Scraping may violate Instagram's Terms of Use. Use it only on content you are allowed to access, respect privacy
and applicable law, and keep the collected data secure.

## License
[MIT](LICENSE.md). Original work by AgiMaulana.
