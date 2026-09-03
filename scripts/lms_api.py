"""Локальная имитация REST API LMS (JSON/CSV).

    python scripts/lms_api.py
    GET http://127.0.0.1:8765/api/lms/schedule
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edu_curator.lms.stub import LMSStub  # noqa: E402

lms = LMSStub()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stdout.write("[lms-api] " + (fmt % args) + "\n")

    def _send(self, code: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        mapping = {
            "/api/lms/schedule": (json.dumps(lms.get_schedule(), ensure_ascii=False, indent=2), "application/json; charset=utf-8"),
            "/api/lms/modules": (json.dumps(lms.get_modules(), ensure_ascii=False, indent=2), "application/json; charset=utf-8"),
            "/api/lms/students": (json.dumps(lms.get_students(), ensure_ascii=False, indent=2), "application/json; charset=utf-8"),
            "/api/lms/assignments": (
                json.dumps(lms.get_assignments(), ensure_ascii=False, indent=2),
                "application/json; charset=utf-8",
            ),
            "/api/lms/export/schedule.csv": (lms.export_schedule_csv(), "text/csv; charset=utf-8"),
            "/api/lms/export/assignments.json": (lms.export_assignments_json(), "application/json; charset=utf-8"),
            "/health": (json.dumps({"status": "ok", "service": "lms-stub"}), "application/json"),
        }
        if path in mapping:
            body, ctype = mapping[path]
            self._send(200, body, ctype)
            return
        catalog = {
            "service": "EduPath LMS stub",
            "disclaimer": "Вымышленные учебные данные",
            "endpoints": list(mapping),
        }
        self._send(200 if path == "/" else 404, json.dumps(catalog, ensure_ascii=False, indent=2), "application/json; charset=utf-8")


def main() -> None:
    host = os.environ.get("LMS_API_HOST", "127.0.0.1")
    port = int(os.environ.get("LMS_API_PORT", "8765"))
    print(f"LMS stub: http://{host}:{port}/", flush=True)
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
