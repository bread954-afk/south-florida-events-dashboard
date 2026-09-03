import argparse
from pathlib import Path
import requests

from scripts.collectors.base import UA
from scripts.collectors.browser import render_html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--wait")
    args = parser.parse_args()

    if args.browser:
        html = render_html(args.url, args.wait)
    else:
        response = requests.get(args.url, headers={"User-Agent": UA}, timeout=30)
        response.raise_for_status()
        html = response.text

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"saved {len(html)} bytes to {path}")


if __name__ == "__main__":
    main()
