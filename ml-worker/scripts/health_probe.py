"""Tiny readiness/liveness HTTP server for the ml-worker container.

Section F deliverable. Used by the Wave 6 `prod-no-models` Docker target so
Kubernetes / docker-compose health checks can poll cheap endpoints without
loading the heavy Celery imports.

Endpoints
---------
GET /live  -> 200 always (process is alive)
GET /ready -> 200 if production_orchestrator.health()['initialized'] else 503

Run with:
    python -m scripts.health_probe
or:
    ML_HEALTH_PORT=8003 python ml-worker/scripts/health_probe.py

The probe imports `worker` lazily so it can run as a sidecar even when the
orchestrator failed to come up. If the import itself raises, /ready returns
503 with the error reason in the body.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger("ml-worker.health_probe")


def _get_orchestrator_health() -> tuple[int, dict]:
    try:
        # Importing `worker` triggers Celery app creation but not signals.
        # production_orchestrator stays None until worker_ready fires inside
        # the Celery process; this probe checks the *current process's*
        # orchestrator state when run alongside a worker (shared module),
        # otherwise reports not-initialized.
        import worker  # type: ignore  # noqa: WPS433
        orch = getattr(worker, "production_orchestrator", None)
        if orch is None:
            return 503, {"initialized": False, "reason": "orchestrator is None"}
        payload = orch.health()
        code = 200 if payload.get("initialized") else 503
        return code, payload
    except Exception as e:  # pragma: no cover
        return 503, {"initialized": False, "error": str(e)}


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/live":
            self._send(200, {"status": "alive"})
            return
        if self.path == "/ready":
            code, payload = _get_orchestrator_health()
            self._send(code, payload)
            return
        self._send(404, {"error": "not_found", "path": self.path})

    def log_message(self, fmt: str, *args) -> None:  # silence default stderr noise
        logger.debug(fmt, *args)


def main() -> int:
    port = int(os.getenv("ML_HEALTH_PORT", "8003"))
    server = HTTPServer(("0.0.0.0", port), _Handler)
    logger.info("ml-worker health probe listening on :%d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
