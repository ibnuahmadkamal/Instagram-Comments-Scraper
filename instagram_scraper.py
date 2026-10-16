import json
import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import constants as C
import excel_exporter
from config import ScraperConfig


class InstagramCommentScraper:
    """Scrape comments of an Instagram post or reel. Selectors live in constants.py."""

    def __init__(self, config: ScraperConfig, driver: webdriver.Chrome | None = None) -> None:
        self.config: ScraperConfig = config
        self.driver: webdriver.Chrome | None = driver
        self.mode: str = self._detect_mode(config.url)
        self.shortcode: str | None = self._detect_shortcode(config.url)
        self.comments_open: bool = False  # once open, "Close"-like popup buttons must not be clicked

    # ---- entrypoint -------------------------------------------------------------------------
    def run(self) -> None:
        self.driver = self.driver or self._start_driver()
        try:
            self.open_page()
            self.ensure_logged_in()
            self.open_comments()
            self.load_all_comments()
            rows: list[tuple[str, str, bool]] = self.extract_comments()
            if self.config.include_hidden:
                rows = self._merge_hidden(rows)
            self.export(rows)
        finally:
            self.driver.quit()

    # ---- setup ------------------------------------------------------------------------------
    @staticmethod
    def _detect_mode(url: str) -> str:
        match: re.Match[str] | None = re.search(C.SHORTCODE_RE, url)
        return C.KIND_TO_MODE[match.group(1)] if match else C.MODE_POST

    @staticmethod
    def _detect_shortcode(url: str) -> str | None:
        match: re.Match[str] | None = re.search(C.SHORTCODE_RE, url)
        return match.group(2) if match else None

    @staticmethod
    def _start_driver() -> webdriver.Chrome:
        # Persistent profile: login (and 2FA code) only needed once, session is reused next runs.
        options: webdriver.ChromeOptions = webdriver.ChromeOptions()
        options.add_argument("--user-data-dir=" + os.path.abspath(C.CHROME_PROFILE_DIR))
        return webdriver.Chrome(options=options)

    def _wait(self, timeout: int) -> WebDriverWait:
        return WebDriverWait(self.driver, timeout)

    # ---- page / login -----------------------------------------------------------------------
    def open_page(self) -> None:
        # Go straight to the post/reel. Saved profile => already logged in => no login step.
        self.driver.get(self.config.url)
        try:
            self._wait(C.LOGIN_WAIT_SECONDS).until(lambda d: self.login_form_visible() or self.page_ready())
        except Exception:
            pass

    def login_form_visible(self) -> bool:
        return any(e.is_displayed() for e in self.driver.find_elements(By.CSS_SELECTOR, C.LOGIN_PASSWORD_CSS))

    def page_ready(self) -> bool:
        if self.driver.find_elements(By.CSS_SELECTOR, C.POST_LOADED_CSS):
            return True
        return bool(self.driver.find_elements(By.XPATH, C.COMMENT_ICON_XPATH))  # reel feed has no <article>

    def ensure_logged_in(self) -> None:
        needs_login: bool = self.login_form_visible()
        print("Login required" if needs_login else "Already logged in, skipping login")
        if not needs_login:
            return
        if not self.config.ig_username or not self.config.ig_password:
            sys.exit("Set IG_USERNAME and IG_PASSWORD in .env")

        username: WebElement = self._wait(C.ELEMENT_WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, C.LOGIN_USERNAME_CSS))
        )
        username.send_keys(self.config.ig_username)
        password: WebElement = self._wait(C.ELEMENT_WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, C.LOGIN_PASSWORD_CSS))
        )
        password.send_keys(self.config.ig_password)
        password.submit()

        self._handle_verification_code()
        try:
            self._wait(C.POST_LOGIN_WAIT_SECONDS).until(lambda d: not self.login_form_visible())
        except Exception:
            pass
        time.sleep(self.config.sleep_after_login)
        self.dismiss_popups()
        self.driver.get(self.config.url)
        try:
            self._wait(C.ELEMENT_WAIT_SECONDS).until(lambda d: self.page_ready())
        except Exception:
            pass

    def _find_code_input(self, timeout: int) -> WebElement | None:
        try:
            return self._wait(timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, C.VERIFICATION_CODE_CSS))
            )
        except Exception:
            return None

    def _handle_verification_code(self) -> None:
        """Ask the 2FA code in the terminal, type it into the browser, repeat while rejected."""
        code_input: WebElement | None = self._find_code_input(C.CODE_FIELD_WAIT_SECONDS)
        while code_input is not None:
            code: str = input("Instagram verification code: ").strip()
            code_input.clear()
            code_input.send_keys(code)
            code_input.send_keys(Keys.ENTER)
            time.sleep(C.CODE_SUBMIT_SLEEP_SECONDS)
            code_input = self._find_code_input(C.CODE_RECHECK_WAIT_SECONDS)
            if code_input is not None:
                print("Code rejected, try again.")

    def dismiss_popups(self, rounds: int = 3) -> int:
        """Close 'Save login info', 'Turn on notifications' etc. Returns number of clicks."""
        labels: tuple[str, ...] = C.POPUP_LABELS_SAFE if self.comments_open else C.POPUP_LABELS
        xpath: str = " | ".join(
            f"//button[normalize-space()='{t}'] | //div[@role='button'][normalize-space()='{t}']"
            f" | //*[@role='dialog']//*[@aria-label='{t}']"
            for t in labels
        )
        total: int = 0
        for _ in range(rounds):
            clicked: int = 0
            for el in self.driver.find_elements(By.XPATH, xpath):
                try:
                    if el.is_displayed():
                        self.driver.execute_script("arguments[0].click();", el)
                        clicked += 1
                        time.sleep(C.POPUP_CLICK_SLEEP_SECONDS)
                except Exception:
                    pass
            total += clicked
            if not clicked:
                break
        return total

    # ---- comments ---------------------------------------------------------------------------
    def count_comments(self) -> int:
        return int(self.driver.execute_script(C.COUNT_COMMENTS_JS))

    def comments_visible(self, timeout: int) -> bool:
        try:
            self._wait(timeout).until(lambda d: self.count_comments() > 0)
            return True
        except Exception:
            return False

    def _click(self, element: WebElement) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.driver.execute_script("arguments[0].click();", element)

    def _target_comment_button(self) -> WebElement | None:
        """Comment button of the target reel card (reel/reel_feed), else first displayed comment icon."""
        if self.mode != C.MODE_POST and self.shortcode:
            card_button: WebElement | None = self.driver.execute_script(
                C.REEL_CARD_COMMENT_BUTTON_JS, self.shortcode
            )
            if card_button is not None:
                return card_button
        icons: list[WebElement] = self.driver.find_elements(By.XPATH, C.COMMENT_ICON_XPATH)
        displayed: list[WebElement] = [i for i in icons if i.is_displayed()]
        return displayed[0] if displayed else None

    def open_comments(self) -> None:
        """Post page loaded != comments loaded. Open the comment panel if needed; dump debug info on failure."""
        self.dismiss_popups(1)
        if self.comments_visible(C.FIRST_COMMENT_CHECK_SECONDS):
            self.comments_open = True
            return

        button: WebElement | None = self._target_comment_button()
        if button is not None:
            try:
                self._click(button)
                print("Clicked comment icon")
            except Exception as exc:
                print(f"Comment icon click failed: {exc.__class__.__name__}")
            if self.comments_visible(self.config.wait_comments):
                self.comments_open = True
                return

        if self.mode != C.MODE_REEL_FEED:  # lazy-loaded below the fold (never scroll the reel feed)
            for _ in range(C.SCROLL_FALLBACK_ATTEMPTS):
                self.driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                if self.comments_visible(C.SCROLL_FALLBACK_WAIT_SECONDS):
                    self.comments_open = True
                    return
        self._dump_debug(button is not None)

    def _click_visible(self, xpath: str) -> int:
        clicked: int = 0
        for btn in self.driver.find_elements(By.XPATH, xpath)[: C.CLICK_LIMIT_PER_ROUND]:
            try:
                if btn.is_displayed():
                    self._click(btn)
                    clicked += 1
                    time.sleep(self.config.sleep_click)
            except Exception:
                pass
        return clicked

    def load_all_comments(self) -> int:
        """Rounds of: load-more + expand replies + scroll. Stops on max rounds, MAX_COMMENTS or no progress."""
        rounds: int = 0
        stale_rounds: int = 0
        prev_count: int = -1
        count: int = self.count_comments()
        allow_window_scroll: bool = self.mode != C.MODE_REEL_FEED
        while rounds < self.config.max_rounds and stale_rounds < C.STALE_ROUNDS_LIMIT:
            self.dismiss_popups(1)
            clicked: int = self._click_visible(C.LOAD_MORE_XPATH) + self._click_visible(C.REPLIES_XPATH)
            self.driver.execute_script(C.SCROLL_COMMENTS_JS, allow_window_scroll)
            rounds += 1
            time.sleep(self.config.sleep_scroll)
            count = self.count_comments()
            print(f"round {rounds}: {count} comments, clicked {clicked}")
            if self.config.max_comments and count >= self.config.max_comments:
                print(f"reached MAX_COMMENTS={self.config.max_comments}")
                break
            stale_rounds = stale_rounds + 1 if (count == prev_count and clicked == 0) else 0
            prev_count = count
        return count

    def _extract_raw(self) -> list[list[str]]:
        return self.driver.execute_script(C.EXTRACT_COMMENTS_JS)

    def extract_comments(self) -> list[tuple[str, str, bool]]:
        """Visible comments as (name, text, is_hidden=False)."""
        rows: list[tuple[str, str, bool]] = [(n, t, False) for n, t, _href in self._extract_raw()]
        print(f"scraped {len(rows)} comments")
        return rows

    def _merge_hidden(self, rows: list[tuple[str, str, bool]]) -> list[tuple[str, str, bool]]:
        """Open "View hidden comments" (if present), load them, append the ones not already scraped."""
        known: set[tuple[str, str]] = {(n, t) for n, t, _ in rows}
        buttons: list[WebElement] = [
            b for b in self.driver.find_elements(By.XPATH, C.HIDDEN_COMMENTS_XPATH) if b.is_displayed()
        ]
        if not buttons:
            print("no hidden comments section found")
            return rows
        try:
            self._click(buttons[-1])  # innermost match is last in document order
            print("Opened hidden comments")
        except Exception as exc:
            print(f"Hidden comments click failed: {exc.__class__.__name__}")
            return rows
        self.comments_visible(self.config.wait_comments)
        self.load_all_comments()
        added: list[tuple[str, str, bool]] = []
        for name, text, _href in self._extract_raw():
            if (name, text) not in known:
                known.add((name, text))
                added.append((name, text, True))
        print(f"hidden comments added: {len(added)}")
        return rows + added

    def export(self, rows: list[tuple[str, str, bool]]) -> None:
        if self.config.max_comments:
            rows = rows[: self.config.max_comments]
        names: list[str] = [n for n, _, _ in rows]
        comments: list[str] = [t for _, t, _ in rows]
        hidden: list[bool] = [h for _, _, h in rows]
        excel_exporter.export(names, comments, self.config.url, self.config.out_name, hidden)
        print(f"saved {self.config.out_name} ({len(rows)} rows)")

    # ---- debug ------------------------------------------------------------------------------
    def _dump_debug(self, icon_clicked: bool) -> None:
        """Screenshot + page source + counts-only state, so a failing page can be analysed."""
        self.driver.save_screenshot(C.DEBUG_SCREENSHOT)
        with open(C.DEBUG_HTML, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        state: dict = self.driver.execute_script(C.DEBUG_STATE_JS)
        state.update({"mode": self.mode, "iconClicked": icon_clicked, "shortcodeFound": bool(self.shortcode)})
        with open(C.DEBUG_JSON, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        print(
            f"WARNING: no comments detected (mode={self.mode}). "
            f"Saved {C.DEBUG_SCREENSHOT}, {C.DEBUG_HTML}, {C.DEBUG_JSON}"
        )
