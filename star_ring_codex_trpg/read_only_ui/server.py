from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict
from urllib.parse import parse_qs, urlparse
import argparse
import json
import mimetypes

from ..errors import StarRingCodexError, UiRequestError
from .controller import (
    build_front_free_action_payload,
    build_front_load_session_payload,
    build_front_next_session_payload,
    build_front_play_payload,
    build_front_snapshot_payload,
    build_free_action_payload,
    build_gpt_free_action_payload,
    build_gpt_load_session_payload,
    build_gpt_next_session_payload,
    build_gpt_play_payload,
    build_gpt_read_model_payload,
    build_load_session_payload,
    build_next_session_payload,
    build_play_payload,
    build_save_session_payload,
    build_ui_payload,
    free_action_request_from_body,
    load_session_request_from_body,
    next_session_request_from_body,
    play_request_from_body,
    save_session_request_from_body,
    viewer_request_from_query,
)


STATIC_ROOT = Path(__file__).resolve().parent / "static"


class ReadOnlyUiHandler(BaseHTTPRequestHandler):
    server_version = "StarRingCodexTRPGReadOnlyUI/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html")
            return
        if parsed.path == "/app.js":
            self._serve_static("app.js")
            return
        if parsed.path == "/styles.css":
            self._serve_static("styles.css")
            return
        if parsed.path == "/api/bundle":
            self._serve_bundle_api(parse_qs(parsed.query))
            return
        if parsed.path == "/api/front/snapshot":
            self._serve_front_snapshot_api(parse_qs(parsed.query))
            return
        if parsed.path == "/api/gpt-read-model":
            self._serve_gpt_read_model_api(parse_qs(parsed.query))
            return
        if parsed.path == "/health":
            self._write_json(200, {"ok": True})
            return
        self._write_json(404, {"error": f"Unknown path: {parsed.path}"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/play":
            self._serve_play_api()
            return
        if parsed.path == "/api/front/play":
            self._serve_front_play_api()
            return
        if parsed.path == "/api/gpt/play":
            self._serve_gpt_play_api()
            return
        if parsed.path == "/api/free-action":
            self._serve_free_action_api()
            return
        if parsed.path == "/api/front/free-action":
            self._serve_front_free_action_api()
            return
        if parsed.path == "/api/gpt/free-action":
            self._serve_gpt_free_action_api()
            return
        if parsed.path == "/api/save-session":
            self._serve_save_session_api()
            return
        if parsed.path == "/api/load-session":
            self._serve_load_session_api()
            return
        if parsed.path == "/api/front/load-session":
            self._serve_front_load_session_api()
            return
        if parsed.path == "/api/gpt/load-session":
            self._serve_gpt_load_session_api()
            return
        if parsed.path == "/api/next-session":
            self._serve_next_session_api()
            return
        if parsed.path == "/api/front/next-session":
            self._serve_front_next_session_api()
            return
        if parsed.path == "/api/gpt/next-session":
            self._serve_gpt_next_session_api()
            return
        self._write_json(404, {"error": f"Unknown path: {parsed.path}"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _serve_static(self, filename: str) -> None:
        target = STATIC_ROOT / filename
        if not target.exists():
            self._write_json(404, {"error": f"Static asset not found: {filename}"})
            return
        body = target.read_bytes()
        content_type, _ = mimetypes.guess_type(target.name)
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_bundle_api(self, query: Dict[str, list[str]]) -> None:
        try:
            request = viewer_request_from_query(query)
            payload = build_ui_payload(request)
            self._write_json(200, payload)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_front_snapshot_api(self, query: Dict[str, list[str]]) -> None:
        try:
            request = viewer_request_from_query(query)
            payload = build_front_snapshot_payload(request)
            self._write_json(200, payload)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_gpt_read_model_api(self, query: Dict[str, list[str]]) -> None:
        try:
            request = viewer_request_from_query(query)
            payload = build_gpt_read_model_payload(request)
            self._write_json(200, payload)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_play_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = play_request_from_body(payload)
            response = build_play_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_front_play_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = play_request_from_body(payload, prefer_world_json_when_both=True)
            response = build_front_play_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_gpt_play_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = play_request_from_body(payload, prefer_world_json_when_both=True)
            response = build_gpt_play_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_free_action_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = free_action_request_from_body(payload)
            response = build_free_action_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_front_free_action_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = free_action_request_from_body(payload, prefer_world_json_when_both=True)
            response = build_front_free_action_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_gpt_free_action_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = free_action_request_from_body(payload, prefer_world_json_when_both=True)
            response = build_gpt_free_action_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_save_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = save_session_request_from_body(payload)
            response = build_save_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_load_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = load_session_request_from_body(payload)
            response = build_load_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_front_load_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = load_session_request_from_body(payload)
            response = build_front_load_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_gpt_load_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = load_session_request_from_body(payload)
            response = build_gpt_load_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_next_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = next_session_request_from_body(payload)
            response = build_next_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_front_next_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = next_session_request_from_body(payload)
            response = build_front_next_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _serve_gpt_next_session_api(self) -> None:
        try:
            payload = self._read_json_body()
            request = next_session_request_from_body(payload)
            response = build_gpt_next_session_payload(request)
            self._write_json(200, response)
        except StarRingCodexError as exc:
            self._write_json(400, {"error": str(exc)})

    def _read_json_body(self) -> Dict[str, object]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw_body = self.rfile.read(length)
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise UiRequestError(f"Invalid JSON body: {exc.msg}") from exc
        if not isinstance(body, dict):
            raise UiRequestError("JSON body must be an object.")
        return body

    def _write_json(self, status_code: int, payload: Dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="StarRingCodexTRPG read-only local web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), ReadOnlyUiHandler)
    print(f"Read-only UI listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
