import re
import sys

import constants as C
from config import ScraperConfig
from instagram_scraper import InstagramCommentScraper


def main() -> None:
    # Ask target URL + output filename before opening the browser.
    url: str = input("Instagram post/reel URL: ").strip()
    if not url:
        sys.exit("URL is required")

    match: re.Match[str] | None = re.search(C.SHORTCODE_RE, url)
    default_name: str = f"comments_{match.group(2)}" if match else "comments"
    out_name: str = input(f"Output file name [{default_name}]: ").strip() or default_name
    if not out_name.lower().endswith(".xlsx"):
        out_name += ".xlsx"

    config: ScraperConfig = ScraperConfig.from_env(url, out_name)
    InstagramCommentScraper(config).run()


if __name__ == "__main__":
    main()
