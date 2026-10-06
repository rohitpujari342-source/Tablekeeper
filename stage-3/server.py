"""HTTP entry point for the Tablekeeper Stage 1 service."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from app.domain import DomainError
from app.service import ApiResponse, TablekeeperService


MAX_REQUEST_BYTES = 5 * 1024 * 1024


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


class TablekeeperHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False
    request_queue_size = 128

    def __init__(self, address: tuple[str, int], loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(address, TablekeeperHandler)
        self.loop = loop
        self.service = TablekeeperService()


class TablekeeperHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: TablekeeperHTTPServer

    def do_GET(self) -> None:
        self._process()

    def do_POST(self) -> None:
        self._process()

    def do_PATCH(self) -> None:
        self._process()

    def do_PUT(self) -> None:
        self._process()

    def do_DELETE(self) -> None:
        self._process()

    def do_OPTIONS(self) -> None:
        self._process()

    def do_HEAD(self) -> None:
        self._process(head_only=True)

    def _process(self, *, head_only: bool = False) -> None:
        try:
            body = self._read_body()
            payload: Any = None
            if body:
                try:
                    payload = json.loads(body.decode("utf-8"), parse_constant=_reject_constant)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
                    raise DomainError(400, "malformed_request", "request body is not valid JSON") from exc

            headers = {key.lower(): value for key, value in self.headers.items()}
            future = asyncio.run_coroutine_threadsafe(
                self.server.service.handle(self.command, self.path, headers, payload),
                self.server.loop,
            )
            response = future.result(timeout=15)
            self._write_response(response, head_only=head_only)
        except DomainError as exc:
            self._write_response(ApiResponse(exc.status, exc.error_body()), head_only=head_only)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self._write_response(
                ApiResponse(500, {"error": {"code": "internal_error", "message": "internal server error"}}),
                head_only=head_only,
            )

    def _read_body(self) -> bytes:
        transfer_encoding = self.headers.get("Transfer-Encoding")
        if transfer_encoding:
            raise DomainError(400, "malformed_request", "transfer-encoded request bodies are unsupported")
        length_value = self.headers.get("Content-Length")
        if length_value is None:
            return b""
        try:
            length = int(length_value)
        except ValueError as exc:
            raise DomainError(400, "malformed_request", "invalid Content-Length") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise DomainError(400, "malformed_request", "request body is too large")
        data = self.rfile.read(length)
        if len(data) != length:
            raise DomainError(400, "malformed_request", "incomplete request body")
        return data

    def _write_response(self, response: ApiResponse, *, head_only: bool = False) -> None:
        if response.status == 204 or response.body is None:
            payload = b""
        elif isinstance(response.body, bytes):
            payload = response.body
        elif isinstance(response.body, str):
            payload = response.body.encode("utf-8")
        else:
            payload = json.dumps(
                response.body,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        content_type = getattr(response, "content_type", "application/json; charset=utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if payload and not head_only:
            self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


async def _serve() -> None:
    try:
        port = int(os.environ.get("PORT", "8080"))
    except ValueError as exc:
        raise SystemExit("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535")
    loop = asyncio.get_running_loop()
    server = TablekeeperHTTPServer(("0.0.0.0", port), loop)
    thread = threading.Thread(target=server.serve_forever, name="tablekeeper-http", daemon=True)
    thread.start()
    print(f"Tablekeeper Stage 3 listening on 0.0.0.0:{port}", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    asyncio.run(_serve())