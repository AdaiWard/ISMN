from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a consistent SQLite backup")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise SystemExit("This helper supports SQLite only")
    source = Path(url.removeprefix("sqlite:///"))
    destination = args.destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    print(f"Backup created: {destination}")


if __name__ == "__main__":
    main()

