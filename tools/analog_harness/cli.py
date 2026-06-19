#!/usr/bin/env python3
"""CLI for the adaptive analog closure harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_harness_config
from .controller import HarnessController


DEFAULT_CONFIG = "tools/analog_harness/configs/smcnr_se_2st_amp.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or inspect the analog closure harness.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run sizing, simulation, layout evidence collection, and feedback.")
    run.add_argument("--config", default=DEFAULT_CONFIG)
    run.add_argument("--max-candidates", type=int, default=1)
    run.add_argument("--batch-size", type=int, default=1)
    run.add_argument("--layout-budget", type=int, default=1)
    run.add_argument("--skip-layout", action="store_true")
    run.add_argument("--skip-sim", action="store_true")
    run.add_argument("--force-sizing", action="store_true", help="Ignore front-end results and call GRPO sizing first.")
    run.add_argument("--no-frontend-results", action="store_true", help="Disable front-end result reuse.")
    run.add_argument("--no-knowledge-archive", action="store_true", help="Do not update the GRPO warm-start archive.")

    resume = sub.add_parser("resume", help="Resume a previous harness run from the configured run directory.")
    resume.add_argument("--config", default=DEFAULT_CONFIG)
    resume.add_argument("--max-candidates", type=int, default=1)
    resume.add_argument("--batch-size", type=int, default=1)
    resume.add_argument("--layout-budget", type=int, default=1)
    resume.add_argument("--skip-layout", action="store_true")
    resume.add_argument("--skip-sim", action="store_true")
    resume.add_argument("--force-sizing", action="store_true", help="Ignore front-end results and call GRPO sizing first.")
    resume.add_argument("--no-frontend-results", action="store_true", help="Disable front-end result reuse.")
    resume.add_argument("--no-knowledge-archive", action="store_true", help="Do not update the GRPO warm-start archive.")

    summarize = sub.add_parser("summarize", help="Print the current run summary.")
    summarize.add_argument("--config", default=DEFAULT_CONFIG)
    train = sub.add_parser("train-grpo", help="Prepare the GRPO warm-start long-training interface without running it.")
    train.add_argument("--config", default=DEFAULT_CONFIG)
    train.add_argument("--steps", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_harness_config(Path(args.config))
    controller = HarnessController(config)
    if args.command in {"run", "resume"}:
        summary = controller.run(
            max_candidates=max(1, args.max_candidates),
            batch_size=max(1, args.batch_size),
            layout_budget=max(0, args.layout_budget),
            skip_layout=bool(args.skip_layout),
            skip_sim=bool(args.skip_sim),
            use_frontend_results=not bool(args.no_frontend_results),
            force_sizing=bool(args.force_sizing),
            archive_good_models=not bool(args.no_knowledge_archive),
        )
    elif args.command == "summarize":
        summary = controller.summarize()
    elif args.command == "train-grpo":
        summary = controller.prepare_grpo_training(steps=max(1, args.steps))
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
