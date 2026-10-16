import os
from dataclasses import dataclass

from dotenv import load_dotenv

from constants import DEFAULTS


@dataclass(frozen=True)
class ScraperConfig:
    url: str
    out_name: str
    sleep_scroll: float
    sleep_click: float
    sleep_after_login: float
    wait_comments: int
    max_rounds: int
    max_comments: int
    include_hidden: bool
    ig_username: str | None
    ig_password: str | None

    @classmethod
    def from_env(cls, url: str, out_name: str) -> "ScraperConfig":
        load_dotenv()

        def env(key: str) -> str:
            return os.getenv(key, DEFAULTS[key])

        # IG_USERNAME, not USERNAME: the OS already defines USERNAME and load_dotenv won't override it.
        return cls(
            url=url,
            out_name=out_name,
            sleep_scroll=float(env("SLEEP_SCROLL_SECONDS")),
            sleep_click=float(env("SLEEP_CLICK_SECONDS")),
            sleep_after_login=float(env("SLEEP_AFTER_LOGIN_SECONDS")),
            wait_comments=int(env("WAIT_COMMENTS_SECONDS")),
            max_rounds=int(env("LOAD_COMMENT_CLICKS")),
            max_comments=int(env("MAX_COMMENTS")),
            include_hidden=env("INCLUDE_HIDDEN_COMMENTS").strip().lower() in ("1", "true", "yes"),
            ig_username=os.getenv("IG_USERNAME"),
            ig_password=os.getenv("IG_PASSWORD"),
        )
