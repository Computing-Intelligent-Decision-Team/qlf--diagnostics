"""Contract tests for the live-only PCS-Harness workflow API."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from run_service import ActiveRunError, RunService, UnsupportedClosureError  # noqa: E402


VERIFIED_NETLIST = (
    "subckt ota_core VINP VINM IB VDD VOUT GND\n"
    "M1 (VOUT VINP GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1u nf=2\n"
    "ends ota_core\n"
)


class _FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.pid = 4242

    def poll(self) -> int | None:
        return self.returncode


class WorkflowApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pcs_root = self.root / "pcs"
        netlist = self.pcs_root / "examples/ota_core_sky130_try/ota_core_magical.sp"
        netlist.parent.mkdir(parents=True)
        netlist.write_text(VERIFIED_NETLIST, encoding="utf-8")
        configs = self.pcs_root / "tools/analog_harness/configs"
        configs.mkdir(parents=True)
        self.profile = configs / "ota_core_workflow_demo.yaml"
        self.profile.write_text(
            "design_id: ota_core\ntop_cell: ota_core\ncircuit_kind: ota\n",
            encoding="utf-8",
        )
        (configs / "inverter_core.yaml").write_text(
            "design_id: inverter_core\ntop_cell: inverter_core\ncircuit_kind: inverter\n",
            encoding="utf-8",
        )
        self.launches: list[dict] = []

        def launch(command, **kwargs):
            process = _FakeProcess()
            self.launches.append({"command": command, "kwargs": kwargs, "process": process})
            return process

        self.service = RunService(
            pcs_root=self.pcs_root,
            runs_root=self.root / "runs",
            verified_netlist=netlist,
            verified_profile=self.profile,
            launcher=launch,
            python_executable=Path(sys.executable),
        )
        self.app = create_app(self.service)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_registry_and_verified_ota_parse_preflight(self) -> None:
        status, payload, _headers = self._json_request("GET", "/api/circuit-types")
        self.assertEqual(status, 200)
        by_id = {item["id"]: item for item in payload["items"]}
        self.assertTrue(by_id["ota"]["demo_ready"])
        self.assertFalse(by_id["inverter"]["demo_ready"])

        status, parsed, _headers = self._json_request(
            "POST",
            "/api/netlists/parse",
            {"circuit_type": "ota", "filename": "uploaded.sp", "content": VERIFIED_NETLIST},
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed["netlist"]["top_cell"], "ota_core")
        self.assertEqual(parsed["netlist"]["ports"], ["VINP", "VINM", "IB", "VDD", "VOUT", "GND"])
        self.assertEqual(parsed["netlist"]["device_counts"], {"M": 1})
        self.assertTrue(parsed["preflight"]["ready"])
        self.assertEqual(parsed["binding"]["profile_path"], str(self.profile.resolve()))
        self.assertEqual(len(parsed["binding"]["profile_sha256"]), 64)

    def test_arbitrary_or_modified_netlist_cannot_start_verified_closure(self) -> None:
        parsed = self.service.parse_netlist(
            circuit_type="ota",
            filename="different.cir",
            content=VERIFIED_NETLIST.replace("w=1u", "w=2u"),
        )
        self.assertFalse(parsed["preflight"]["ready"])
        self.assertEqual(parsed["preflight"]["code"], "verified_input_hash_mismatch")
        with self.assertRaises(UnsupportedClosureError):
            self.service.start_run(parsed["parse_id"])

        unsupported = self.service.parse_netlist(
            circuit_type="inverter",
            filename="inverter.spice",
            content=".subckt inverter A Y VDD GND\n.ends inverter\n",
        )
        self.assertFalse(unsupported["preflight"]["ready"])
        self.assertEqual(unsupported["preflight"]["code"], "circuit_type_not_demo_ready")

    def test_run_uses_fresh_root_explicit_environment_and_single_active_guard(self) -> None:
        parsed = self.service.parse_netlist(
            circuit_type="ota", filename="ota.sp", content=VERIFIED_NETLIST
        )
        first = self.service.start_run(parsed["parse_id"])

        self.assertEqual(first["status"], "running")
        self.assertTrue(Path(first["run_root"]).is_dir())
        launch = self.launches[0]
        self.assertEqual(launch["kwargs"]["cwd"], str(self.pcs_root))
        self.assertEqual(launch["kwargs"]["env"]["PCS_WORKFLOW_RUN_ROOT"], first["run_root"])
        self.assertEqual(launch["kwargs"]["env"]["PYTHONUNBUFFERED"], "1")
        self.assertEqual(launch["command"][0], str(Path(sys.executable).resolve()))
        with self.assertRaises(ActiveRunError):
            self.service.start_run(parsed["parse_id"])

    def test_sse_preserves_sequence_and_last_event_id_is_exclusive(self) -> None:
        run = self._start_verified_run()
        events_path = Path(run["events_path"])
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events = [self._event(run["run_id"], sequence) for sequence in (1, 2, 3)]
        events_path.write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
        )

        chunks = list(self.service.event_stream(run["run_id"], after_sequence=1, follow=False))

        body = "".join(chunks)
        self.assertNotIn("id: 1\n", body)
        self.assertLess(body.index("id: 2\n"), body.index("id: 3\n"))
        self.assertIn('"sequence":2', body)
        self.assertIn('"sequence":3', body)

        self.launches[0]["process"].returncode = 0
        status, raw, headers = self._request(
            "GET",
            f"/api/runs/{run['run_id']}/events",
            extra_environ={"HTTP_LAST_EVENT_ID": "2"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/event-stream; charset=utf-8")
        self.assertNotIn(b"id: 2\n", raw)
        self.assertIn(b"id: 3\n", raw)

    def test_artifacts_are_only_resolved_from_event_references(self) -> None:
        run = self._start_verified_run()
        run_root = Path(run["run_root"])
        artifact = run_root / "evidence" / "metrics.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text('{"gbw_hz": 4700000}\n', encoding="utf-8")
        event = self._event(run["run_id"], 1)
        event["artifact_refs"] = [
            {
                "artifact_id": "metrics:abc123",
                "name": "metrics",
                "relative_path": "evidence/metrics.json",
                "sha256": self.service.sha256(artifact),
                "size_bytes": artifact.stat().st_size,
            }
        ]
        Path(run["events_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(run["events_path"]).write_text(json.dumps(event) + "\n", encoding="utf-8")

        resolved = self.service.resolve_artifact(run["run_id"], "metrics:abc123")
        self.assertEqual(resolved, artifact.resolve())
        with self.assertRaises(FileNotFoundError):
            self.service.resolve_artifact(run["run_id"], "../../etc/passwd")

    def _start_verified_run(self) -> dict:
        parsed = self.service.parse_netlist(
            circuit_type="ota", filename="ota.sp", content=VERIFIED_NETLIST
        )
        return self.service.start_run(parsed["parse_id"])

    def _event(self, run_id: str, sequence: int) -> dict:
        return {
            "schema_version": "pcs_harness_workflow_event.v1",
            "run_id": run_id,
            "source": "harness",
            "event_type": "stage.completed",
            "sequence": sequence,
            "occurred_at": "2026-08-26T00:00:00Z",
            "elapsed_ms": float(sequence),
            "payload": {"index": sequence},
            "candidate_id": "cand_0001",
            "stage": "L1",
            "artifact_refs": [],
        }

    def _json_request(self, method: str, path: str, payload: dict | None = None):
        status, body, headers = self._request(method, path, payload)
        return status, json.loads(body or b"{}"), headers

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        extra_environ: dict | None = None,
    ):
        raw = json.dumps(payload or {}).encode("utf-8") if payload is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(raw),
            "wsgi.url_scheme": "http",
            "SERVER_NAME": "test",
            "SERVER_PORT": "80",
        }
        environ.update(extra_environ or {})
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        body = b"".join(self.app(environ, start_response))
        return captured["status"], body, captured["headers"]


if __name__ == "__main__":
    unittest.main()
