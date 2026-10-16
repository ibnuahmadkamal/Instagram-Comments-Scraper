"""Selectors, XPaths, JS snippets and defaults for the Instagram comment scraper. No logic here."""

# --- Browser / files ---------------------------------------------------------------------------
CHROME_PROFILE_DIR: str = ".chrome-profile"
DEBUG_SCREENSHOT: str = "debug_no_comments.png"
DEBUG_HTML: str = "debug_page.html"
DEBUG_JSON: str = "debug_state.json"

# --- URL ---------------------------------------------------------------------------------------
# group 1 = kind (p / reel / reels / tv), group 2 = shortcode
SHORTCODE_RE: str = r"/(p|reel|reels|tv)/([A-Za-z0-9_-]+)"
MODE_POST: str = "post"
MODE_REEL: str = "reel"
MODE_REEL_FEED: str = "reel_feed"  # /reels/<sc>/ = vertical feed, comments open in a per-card popover
KIND_TO_MODE: dict[str, str] = {
    "p": MODE_POST,
    "tv": MODE_POST,
    "reel": MODE_REEL,
    "reels": MODE_REEL_FEED,
}

# --- Waits (seconds) / limits ------------------------------------------------------------------
LOGIN_WAIT_SECONDS: int = 15
ELEMENT_WAIT_SECONDS: int = 20
POST_LOGIN_WAIT_SECONDS: int = 60
CODE_FIELD_WAIT_SECONDS: int = 1
CODE_RECHECK_WAIT_SECONDS: int = 4
CODE_SUBMIT_SLEEP_SECONDS: int = 6
POPUP_CLICK_SLEEP_SECONDS: int = 1
FIRST_COMMENT_CHECK_SECONDS: int = 1
SCROLL_FALLBACK_WAIT_SECONDS: int = 3
SCROLL_FALLBACK_ATTEMPTS: int = 3
STALE_ROUNDS_LIMIT: int = 3
CLICK_LIMIT_PER_ROUND: int = 20

# --- Env defaults (all overridable in .env) ----------------------------------------------------
DEFAULTS: dict[str, str] = {
    "SLEEP_SCROLL_SECONDS": "2",       # pause after each scroll/expand round
    "SLEEP_CLICK_SECONDS": "0.5",      # pause between button clicks
    "SLEEP_AFTER_LOGIN_SECONDS": "2",
    "WAIT_COMMENTS_SECONDS": "6",      # max wait for comments after clicking the comment icon
    "LOAD_COMMENT_CLICKS": "10",       # max rounds of scroll / load more / expand replies
    "MAX_COMMENTS": "0",               # 0 = unlimited
    "INCLUDE_HIDDEN_COMMENTS": "1",    # 1 = also open "View hidden comments" and scrape them
}

# --- Login -------------------------------------------------------------------------------------
LOGIN_USERNAME_CSS: str = (
    "input[name='username'], input[name='email'], "
    "input[aria-label*='username' i], input[aria-label*='email' i]"
)
LOGIN_PASSWORD_CSS: str = "input[name='password'], input[name='pass'], input[type='password']"
VERIFICATION_CODE_CSS: str = (
    "input[name='verificationCode'], input[name='verification_code'], "
    "input[autocomplete='one-time-code'], input[aria-label*='code' i], input[aria-label*='kode' i]"
)

# --- Page readiness ----------------------------------------------------------------------------
PAGE_READY_CSS: str = "main, article"
POST_LOADED_CSS: str = "article, main ul li span[dir='auto']"

# --- Popups ------------------------------------------------------------------------------------
# "Close"/"Tutup" would also close the comments popover, so SAFE labels are used once comments are open.
POPUP_LABELS_SAFE: tuple[str, ...] = ("Not now", "Not Now", "Nanti saja", "Lain kali", "Cancel", "Batal")
POPUP_LABELS: tuple[str, ...] = POPUP_LABELS_SAFE + ("Close", "Tutup")

# --- Comment panel buttons ---------------------------------------------------------------------
COMMENT_ICON_XPATH: str = (
    "//*[name()='svg'][contains(@aria-label, 'omment') or contains(@aria-label, 'omentar')]"
    "/ancestor::*[self::button or @role='button' or self::a][1]"
)
REPLIES_XPATH: str = (
    "//*[@role='button'][(contains(., 'View all') and contains(., 'repl')) "
    "or (contains(., 'Lihat semua') and contains(., 'balasan'))]"
)
LOAD_MORE_XPATH: str = (
    "//*[@aria-label='Load more comments' or @aria-label='Muat lebih banyak komentar']"
    "/ancestor-or-self::*[self::button or @role='button'][1]"
)

# "View hidden comments" / "Lihat komentar tersembunyi" (comments filtered by Instagram). Not verified live.
HIDDEN_COMMENTS_XPATH: str = (
    "//*[self::button or self::a or @role='button' or @role='link']"
    "[contains(., 'idden comment') or contains(., 'omentar tersembunyi') or contains(., 'omentar yang disembunyikan')]"
)

# --- JS ----------------------------------------------------------------------------------------
# Comment permalink = /p|reel|reels|tv/<sc>/[comments/]c/<id>/ wrapping a <time>. Hashed class names are ignored.
COUNT_COMMENTS_JS: str = r"""
const RE = /\/(?:p|reel|reels|tv)\/[^/]+\/(?:comments\/)?c\/[^/]+/;
return [...document.querySelectorAll('a[href*="/c/"]')]
  .filter(a => RE.test(a.getAttribute('href') || '') && a.querySelector('time')).length;
"""

# Returns [[username, text, permalink], ...]. Caption is excluded (its time link has no /c/).
EXTRACT_COMMENTS_JS: str = r"""
const RE = /\/(?:p|reel|reels|tv)\/[^/]+\/(?:comments\/)?c\/[^/]+/;
const out = []; const seen = new Set();
document.querySelectorAll('a[href*="/c/"]').forEach(permalink => {
  const key = permalink.getAttribute('href') || '';
  if (!RE.test(key) || !permalink.querySelector('time') || seen.has(key)) return;
  let header = permalink.parentElement; let userLink = null;
  for (let i = 0; header && i < 4 && !userLink; i++) {   // climb to the row header holding the author link
    header = header.parentElement;
    userLink = header && header.querySelector('a[role="link"]:not([href*="/c/"])');
  }
  if (!userLink) return;
  const name = userLink.textContent.trim();
  const body = header.nextElementSibling;
  const text = body ? body.textContent.replace(/\s+/g, ' ').trim() : '';
  if (!name || !text) return;
  seen.add(key); out.push([name, text, key]);
});
return out;
"""

# arguments[0] = allow window scroll (false in reel-feed mode: scrolling the window moves to another reel).
SCROLL_COMMENTS_JS: str = r"""
const allowWindow = arguments.length ? arguments[0] : true;
const RE = /\/(?:p|reel|reels|tv)\/[^/]+\/(?:comments\/)?c\/[^/]+/;
const links = [...document.querySelectorAll('a[href*="/c/"]')]
  .filter(a => RE.test(a.getAttribute('href') || '') && a.querySelector('time'));
if (links.length) {
  let el = links[links.length - 1].parentElement;
  while (el && el !== document.body) {
    if (el.scrollHeight > el.clientHeight + 5 && /(auto|scroll)/.test(getComputedStyle(el).overflowY)) {
      el.scrollTop = el.scrollHeight; return 'container';
    }
    el = el.parentElement;
  }
}
if (allowWindow) { window.scrollTo(0, document.body.scrollHeight); return 'window'; }
return 'none';
"""

# arguments[0] = shortcode. Finds the comment button of the reel card that holds the target reel link.
REEL_CARD_COMMENT_BUTTON_JS: str = r"""
const sc = arguments[0];
const ICON = 'svg[aria-label*="omment"], svg[aria-label*="omentar"]';
const links = document.querySelectorAll('a[href*="/reels/' + sc + '/"], a[href*="/reel/' + sc + '/"]');
for (const link of links) {
  let card = link;
  while (card.parentElement && card.querySelectorAll(ICON).length === 0) card = card.parentElement;
  if (card.querySelectorAll(ICON).length !== 1) continue;   // link sits outside any single card
  const btn = card.querySelector(ICON).closest('button, [role="button"], a');
  if (btn) return btn;
}
return null;
"""

# Counts only (no personal data) for the debug dump.
DEBUG_STATE_JS: str = r"""
return {
  commentIcons: document.querySelectorAll('svg[aria-label*="omment"], svg[aria-label*="omentar"]').length,
  cLinks: document.querySelectorAll('a[href*="/c/"]').length,
  cLinksWithTime: document.querySelectorAll('a[href*="/c/"] time').length,
  dialogs: document.querySelectorAll('[role="dialog"]').length,
  viewport: [window.innerWidth, window.innerHeight],
};
"""
