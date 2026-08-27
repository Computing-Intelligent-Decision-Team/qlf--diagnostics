#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
WORKSTREAMS = ROOT / "workstreams"


def slugify(value: str) -> str:
    cleaned = []
    for ch in value.strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in {" ", "-", "_"}:
            cleaned.append("_")
    text = "".join(cleaned).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text or "workstream"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new agent workflow workstream skeleton.")
    parser.add_argument("title", help="Human readable workstream title")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args = parser.parse_args()

    slug = slugify(args.title)
    target = WORKSTREAMS / f"{args.date}_{slug}"
    tasks_dir = target / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    idea_path = target / "idea.md"
    tasks_path = target / "tasks.md"
    log_path = target / "execution-log.md"
    sample_task_path = tasks_dir / "T001_placeholder.md"

    if not idea_path.exists():
        idea_text = (TEMPLATES / "idea.md").read_text(encoding="utf-8")
        idea_path.write_text(f"# Idea\n\n## 标题\n\n{args.title}\n\n" + "\n".join(idea_text.splitlines()[4:]) + "\n", encoding="utf-8")
    if not tasks_path.exists():
        tasks_path.write_text((TEMPLATES / "tasks.md").read_text(encoding="utf-8"), encoding="utf-8")
    if not log_path.exists():
        log_path.write_text((TEMPLATES / "execution-log.md").read_text(encoding="utf-8"), encoding="utf-8")
    if not sample_task_path.exists():
        sample_task_path.write_text((TEMPLATES / "task.md").read_text(encoding="utf-8"), encoding="utf-8")

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
