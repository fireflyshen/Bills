#!/usr/bin/env python3
"""Expose the read-only period query over an internal Docker HTTP endpoint."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

try:
    from query_period import (
        DEFAULT_MAX_TRANSACTIONS,
        LEDGER,
        MAX_QUERY_DAYS,
        load_ledger,
        parse_iso_date,
        query_entries,
    )
except ModuleNotFoundError:  # Imported as tools.query_period_server in tests.
    from tools.query_period import (
        DEFAULT_MAX_TRANSACTIONS,
        LEDGER,
        MAX_QUERY_DAYS,
        load_ledger,
        parse_iso_date,
        query_entries,
    )


MAX_BODY_BYTES = 16 * 1024


def execute_query(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")

    start_value = payload.get("start_date")
    end_value = payload.get("end_date")
    if not isinstance(start_value, str) or not isinstance(end_value, str):
        raise ValueError("start_date and end_date must be strings")

    start_date = parse_iso_date(start_value)
    end_date = parse_iso_date(end_value)
    if end_date < start_date:
        raise ValueError("end_date must not be earlier than start_date")

    days = (end_date - start_date).days + 1
    if days > MAX_QUERY_DAYS:
        raise ValueError(f"date range must not exceed {MAX_QUERY_DAYS} days")

    max_transactions = payload.get(
        "max_transactions", DEFAULT_MAX_TRANSACTIONS
    )
    if isinstance(max_transactions, bool) or not isinstance(max_transactions, int):
        raise ValueError("max_transactions must be an integer")
    if not 1 <= max_transactions <= DEFAULT_MAX_TRANSACTIONS:
        raise ValueError(
            f"max_transactions must be between 1 and {DEFAULT_MAX_TRANSACTIONS}"
        )

    result = query_entries(
        load_ledger(LEDGER),
        start_date,
        end_date,
        max_transactions=max_transactions,
    )
    result["ledger"] = str(LEDGER)
    return result


class QueryHandler(BaseHTTPRequestHandler):
    server_version = "BillsLedgerQuery/1"

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if urlparse(self.path).path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if urlparse(self.path).path != "/query":
            self.send_json(404, {"error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= content_length <= MAX_BODY_BYTES:
                raise ValueError(
                    f"request body must be between 1 and {MAX_BODY_BYTES} bytes"
                )
            payload = json.loads(self.rfile.read(content_length))
            self.send_json(200, execute_query(payload))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": "invalid_request", "message": str(exc)})
        except Exception as exc:
            self.send_json(
                500,
                {"error": type(exc).__name__, "message": str(exc)},
            )

    def log_message(self, format: str, *args: Any) -> None:
        # Keep Docker logs useful without leaking request bodies or ledger content.
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Bills period query API.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), QueryHandler)
    print(f"Bills ledger query listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
