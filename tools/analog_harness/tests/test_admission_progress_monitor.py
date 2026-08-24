import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.analog_harness.admission_progress_monitor import render_progress


class TestAdmissionProgressMonitor(unittest.TestCase):
    def test_renders_running_progress(self):
        text = render_progress({"status": "running", "total": 8, "completed": 3, "returncodes": {"0": 3}, "updated_at": "now"})
        self.assertIn("[###-----] 3/8 (37.5%)", text)
        self.assertIn("status: running", text)

    def test_renders_missing_progress(self):
        self.assertIn("waiting", render_progress(None))


if __name__ == "__main__":
    unittest.main()
