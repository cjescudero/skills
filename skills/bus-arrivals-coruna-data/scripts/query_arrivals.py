#!/usr/bin/env python3
"""Query A Coruna bus arrivals directly from HTTP API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from coruna_bus_api import (
    ARRIVALS_URL_TEMPLATE_DEFAULT,
    BusApiError,
    fetch_stop_arrivals,
    find_bus,
    find_line,
    load_catalog,
    resolve_line_id,
    resolve_stop,
)


def _default_catalog_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "coruna_catalog.json"


def _json_print(payload: dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def _error(message: str, code: str, pretty: bool) -> int:
    _json_print({"ok": False, "message": message, "error_code": code}, pretty=pretty)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Query A Coruna bus arrivals (HTTP only, no MCP).")
    parser.add_argument("--stop-id", type=int, help="Stop ID.")
    parser.add_argument("--stop-name", type=str, help="Stop name (requires local catalog).")
    parser.add_argument("--bus-id", type=int, help="Specific bus ID for stop+bus query.")
    parser.add_argument("--line-id", type=int, help="Specific line ID for stop+line query.")
    parser.add_argument("--line-name", type=str, help="Specific line name (requires local catalog).")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=_default_catalog_path(),
        help="Path to static catalog JSON.",
    )
    parser.add_argument(
        "--arrivals-url-template",
        type=str,
        default=ARRIVALS_URL_TEMPLATE_DEFAULT,
        help="Arrival URL template with {stop_id}.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="HTTP timeout.")
    parser.add_argument(
        "--request-profile",
        choices=["auto", "default", "browser"],
        default="auto",
        help="HTTP header profile. auto tries default and browser profiles.",
    )
    parser.add_argument(
        "--retry-403",
        type=int,
        default=2,
        help="Extra retries when API returns 403/429.",
    )
    parser.add_argument(
        "--disable-http-fallback",
        action="store_true",
        help="Disable https->http fallback attempts.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output.")
    args = parser.parse_args()

    if args.stop_id is None and not args.stop_name:
        return _error("Provide --stop-id or --stop-name.", "stop_selector_required", pretty=args.pretty)
    if args.bus_id is not None and (args.line_id is not None or args.line_name):
        return _error(
            "Use either bus selector or line selector, not both.",
            "selector_conflict",
            pretty=args.pretty,
        )

    catalog = load_catalog(args.catalog)

    try:
        stop = resolve_stop(args.stop_id, args.stop_name, catalog)
    except ValueError as exc:
        return _error(
            f"Cannot resolve stop: {exc}.",
            "stop_resolution_error",
            pretty=args.pretty,
        )

    stop_id = int(stop.value["id"])
    stop_name = str(stop.value.get("name") or f"Parada {stop_id}")

    try:
        arrivals = fetch_stop_arrivals(
            stop_id=stop_id,
            catalog=catalog,
            arrivals_url_template=args.arrivals_url_template,
            timeout_seconds=args.timeout_seconds,
            request_profile=args.request_profile,
            retry_403=max(0, int(args.retry_403)),
            allow_http_fallback=not args.disable_http_fallback,
        )
    except BusApiError as exc:
        return _error(str(exc), "api_error", pretty=args.pretty)

    mode = "stop_arrivals"
    if args.bus_id is not None:
        mode = "bus_at_stop"
    elif args.line_id is not None or args.line_name:
        mode = "line_at_stop"

    response: dict[str, Any] = {
        "ok": True,
        "mode": mode,
        "query": {
            "stop_id": stop_id,
            "stop_name": stop_name,
            "matched_by": stop.matched_by,
            "bus_id": args.bus_id,
            "line_id": args.line_id,
            "line_name": args.line_name,
        },
        "source": {
            "arrivals_url": arrivals.get("api_url"),
            "catalog_path": str(args.catalog),
            "catalog_loaded": bool(catalog),
        },
    }

    if mode == "stop_arrivals":
        response["arrivals"] = arrivals
        _json_print(response, pretty=args.pretty)
        return 0

    if mode == "bus_at_stop":
        found = find_bus(arrivals, int(args.bus_id))
        if not found:
            response["ok"] = False
            response["message"] = f"Bus {args.bus_id} not found at stop {stop_id}."
            _json_print(response, pretty=args.pretty)
            return 0

        line, bus = found
        response["line"] = line
        response["bus"] = bus
        _json_print(response, pretty=args.pretty)
        return 0

    # mode == line_at_stop
    try:
        resolved_line_id, line_match = resolve_line_id(args.line_id, args.line_name, catalog)
    except ValueError as exc:
        return _error(
            f"Cannot resolve line: {exc}.",
            "line_resolution_error",
            pretty=args.pretty,
        )

    line = find_line(arrivals, resolved_line_id)
    response["query"]["line_id"] = resolved_line_id
    response["query"]["line_match"] = line_match
    if not line:
        response["ok"] = False
        response["message"] = f"Line {resolved_line_id} has no arrivals at stop {stop_id}."
        _json_print(response, pretty=args.pretty)
        return 0

    response["line"] = line
    _json_print(response, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
