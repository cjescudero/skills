#!/usr/bin/env python3
"""Refresh local static catalog for A Coruna bus stops and lines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coruna_bus_api import BusApiError, CATALOG_URL_DEFAULT, build_catalog_from_api, save_catalog


def _default_catalog_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "coruna_catalog.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh A Coruna static bus catalog (func=7).")
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_catalog_path(),
        help="Output JSON path for static catalog.",
    )
    parser.add_argument(
        "--stops-url",
        type=str,
        default=CATALOG_URL_DEFAULT,
        help="Catalog endpoint URL.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout.")
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
    parser.add_argument("--pretty", action="store_true", help="Print summary JSON.")
    args = parser.parse_args()

    try:
        catalog = build_catalog_from_api(
            stops_url=args.stops_url,
            timeout_seconds=args.timeout_seconds,
            request_profile=args.request_profile,
            retry_403=max(0, int(args.retry_403)),
            allow_http_fallback=not args.disable_http_fallback,
        )
    except BusApiError as exc:
        print(json.dumps({"ok": False, "message": str(exc), "error_code": "api_error"}, ensure_ascii=False))
        return 2

    save_catalog(args.output, catalog)
    summary = {
        "ok": True,
        "output": str(args.output),
        "generated_at": catalog.get("generated_at"),
        "stops": len(catalog.get("stops", [])),
        "lines": len(catalog.get("lines", [])),
        "source_url": catalog.get("source_url"),
    }
    if args.pretty:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
