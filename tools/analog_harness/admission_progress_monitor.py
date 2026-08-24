#!/usr/bin/env python3
"""Read-only terminal monitor for PCS admission-runner progress files."""

import argparse
import json
import time
from pathlib import Path


def render_progress(progress: dict | None) -> str:
    if not progress:
        return "PCS admission: waiting for promotion_progress.json"
    total = int(progress.get("total") or 0)
    completed = int(progress.get("completed") or 0)
    ratio = completed / total if total else 0.0
    filled = round(ratio * 8)
    bar = "#" * filled + "-" * (8 - filled)
    return "\n".join((
        f"PCS admission: [{bar}] {completed}/{total} ({ratio * 100:.1f}%)",
        f"status: {progress.get('status', 'unknown')}",
        f"returncodes: {progress.get('returncodes', {})}",
        f"updated_at: {progress.get('updated_at', 'unknown')}",
    ))


def load_progress(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--interval-s", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    path = args.run_dir / "promotion_progress.json"
    while True:
        print("\033[2J\033[H" + render_progress(load_progress(path)), flush=True)
        progress = load_progress(path)
        if args.once or (progress and progress.get("status") == "finished"):
            return
        time.sleep(max(args.interval_s, 0.2))


if __name__ == "__main__":
    main()
