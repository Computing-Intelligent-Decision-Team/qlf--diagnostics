"""Zero-dependency WSGI API for the live PCS-Harness workflow."""

from __future__ import annotations

import json
import mimetypes
import os
import re
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Callable, Iterable
from wsgiref.simple_server import WSGIServer, make_server

from run_service import ActiveRunError, RunService, UnsupportedClosureError


JsonStart = Callable[[str, list[tuple[str, str]]], Any]


def create_app(service: RunService) -> Callable:
    def application(environ: dict[str, Any], start_response: JsonStart) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")
        try:
            if method == "GET" and path == "/api/circuit-types":
                return _json(start_response, 200, {"items": service.circuit_types()})
            if method == "POST" and path == "/api/netlists/parse":
                body = _read_json(environ)
                return _json(
                    start_response,
                    200,
                    service.parse_netlist(
                        circuit_type=body.get("circuit_type", ""),
                        filename=body.get("filename", ""),
                        content=body.get("content", ""),
                    ),
                )
            if method == "POST" and path == "/api/runs":
                body = _read_json(environ)
                return _json(start_response, 201, service.start_run(body.get("parse_id", "")))
            run_match = re.fullmatch(r"/api/runs/([^/]+)", path)
            if method == "GET" and run_match:
                return _json(start_response, 200, service.run_status(run_match.group(1)))
            events_match = re.fullmatch(r"/api/runs/([^/]+)/events", path)
            if method == "GET" and events_match:
                cursor = int(environ.get("HTTP_LAST_EVENT_ID") or 0)
                start_response(
                    "200 OK",
                    [
                        ("Content-Type", "text/event-stream; charset=utf-8"),
                        ("Cache-Control", "no-cache, no-transform"),
                        ("X-Accel-Buffering", "no"),
                    ],
                )
                return (
                    chunk.encode("utf-8")
                    for chunk in service.event_stream(events_match.group(1), after_sequence=cursor)
                )
            artifact_match = re.fullmatch(r"/api/runs/([^/]+)/artifacts/([^/]+)", path)
            if method == "GET" and artifact_match:
                artifact = service.resolve_artifact(artifact_match.group(1), artifact_match.group(2))
                content_type = mimetypes.guess_type(artifact.name)[0] or "application/octet-stream"
                data = artifact.read_bytes()
                start_response(
                    "200 OK",
                    [("Content-Type", content_type), ("Content-Length", str(len(data)))],
                )
                return [data]
            return _json(start_response, 404, {"error": "not_found"})
        except (ActiveRunError, UnsupportedClosureError) as exc:
            return _json(start_response, 409, {"error": type(exc).__name__, "detail": str(exc)})
        except KeyError as exc:
            return _json(start_response, 404, {"error": "not_found", "detail": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            return _json(start_response, 400, {"error": "invalid_request", "detail": str(exc)})
        except FileNotFoundError as exc:
            return _json(start_response, 404, {"error": "artifact_not_found", "detail": str(exc)})

    return application


def _read_json(environ: dict[str, Any]) -> dict[str, Any]:
    content_type = environ.get("CONTENT_TYPE", "").split(";", 1)[0]
    if content_type != "application/json":
        raise ValueError("Content-Type must be application/json")
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length > RunService.MAX_NETLIST_BYTES + 64 * 1024:
        raise ValueError("request body is too large")
    payload = json.loads(environ["wsgi.input"].read(length) or b"{}")
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload


def _json(start_response: JsonStart, status: int, payload: dict[str, Any]) -> list[bytes]:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    reasons = {200: "OK", 201: "Created", 400: "Bad Request", 404: "Not Found", 409: "Conflict"}
    start_response(
        f"{status} {reasons[status]}",
        [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data)))],
    )
    return [data]


class _ThreadingServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def default_service() -> RunService:
    workspace = Path(os.environ.get("IOT_WORKSPACE", "/home/qlf/IOT")).resolve()
    pcs_root = Path(
        os.environ.get(
            "PCS_HARNESS_ROOT",
            workspace / "references/.codex-worktrees/pcs-harness-workflow",
        )
    ).resolve()
    return RunService(
        pcs_root=pcs_root,
        runs_root=Path(
            os.environ.get(
                "PCS_WORKFLOW_RUNS_ROOT",
                workspace / "generated/analog_harness/ota_core_grpo_demo_20260826/live_runs",
            )
        ),
        verified_netlist=pcs_root / "examples/ota_core_sky130_try/ota_core_magical.sp",
        verified_profile=pcs_root / "tools/analog_harness/configs/ota_core_workflow_demo.yaml",
        python_executable=Path(os.environ.get("PCS_HARNESS_PYTHON", "/home/qlf/anaconda3/envs/Harness/bin/python")),
    )


application = create_app(default_service())


def main() -> None:
    host = os.environ.get("PCS_WORKFLOW_HOST", "127.0.0.1")
    port = int(os.environ.get("PCS_WORKFLOW_PORT", "8765"))
    with make_server(host, port, application, server_class=_ThreadingServer) as server:
        print(f"PCS-Harness Workflow API listening on http://{host}:{port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
