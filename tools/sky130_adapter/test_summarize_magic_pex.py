#!/usr/bin/env python3
"""Tests for Magic PEX summary helpers."""

from __future__ import annotations

import unittest

from summarize_magic_pex import parse_caps, render_summary


class SummarizeMagicPexTest(unittest.TestCase):
    def test_render_summary_includes_output_node_estimate(self) -> None:
        caps = parse_caps(["C0 VOUT GND 2f", "C1 VOUT VDD 3f", "C2 A GND 1f"])

        markdown = render_summary(caps, "example.spice", top=10, output_node="VOUT")

        self.assertIn("## Output Node Estimate", markdown)
        self.assertIn("| `VOUT` | 2 | 5 fF |", markdown)
        self.assertIn("| `GND` | 2 | 3 fF |", markdown)


if __name__ == "__main__":
    unittest.main()
