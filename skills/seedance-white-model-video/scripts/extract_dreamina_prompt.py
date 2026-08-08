#!/usr/bin/env python3
"""Extract the URL-encoded prompt carried by a Dreamina URL."""

from __future__ import annotations

import argparse
import json
from urllib.parse import parse_qs, unquote, urlparse


def extract(url: str) -> dict[str, str]:
    query = parse_qs(urlparse(url).query)
    prompt_values = query.get("prompt", [])
    if not prompt_values:
        raise ValueError("Dreamina URL has no prompt query parameter")
    prompt = unquote(prompt_values[0]).strip()
    return {
        "prompt": prompt,
        "type": query.get("type", [""])[0],
        "workspace": query.get("workspace", [""])[0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Dreamina URL containing a prompt query parameter")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of plain text")
    args = parser.parse_args()
    result = extract(args.url)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["prompt"])


if __name__ == "__main__":
    main()
