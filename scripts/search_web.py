#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.tools.search_provider import UnifiedSearch


def main() -> None:
    parser = argparse.ArgumentParser(description="Search web via Brave and/or Tavily")
    parser.add_argument("query")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--prefer", choices=["auto", "brave", "tavily"], default="auto")
    args = parser.parse_args()

    searcher = UnifiedSearch()
    result = searcher.search(query=args.query, count=args.count, prefer=args.prefer)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
