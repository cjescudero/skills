#!/usr/bin/env python3
"""Core API utilities for A Coruna bus arrivals."""

from __future__ import annotations

import json
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CATALOG_URL_DEFAULT = (
    "https://itranvias.com/queryitr_v3.php?dato=20160101T000000_gl_0_20160101T000000&func=7"
)
ARRIVALS_URL_TEMPLATE_DEFAULT = "https://itranvias.com/queryitr_v3.php?func=0&dato={stop_id}"


class BusApiError(Exception):
    """Raised when the remote API cannot be reached or parsed."""


@dataclass(frozen=True)
class CatalogLookupResult:
    value: dict[str, Any]
    matched_by: str


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _as_dict(value: Any) -> dict[str, Any] | None:
    return value if _is_dict(value) else None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _sort_eta(eta_minutes: int | None) -> int:
    if eta_minutes is None:
        return 10**9
    return eta_minutes


def _first_eta_from_line(line: dict[str, Any]) -> int:
    buses = _as_list(line.get("buses"))
    if not buses:
        return 10**9
    first_bus = _as_dict(buses[0])
    if not first_bus:
        return 10**9
    return _sort_eta(_safe_int(first_bus.get("eta_minutes")))


def _infer_direction(direction_code: int | None, route_index: int) -> str:
    if direction_code == 0:
        return "ida"
    if direction_code == 1:
        return "vuelta"
    if direction_code == 30:
        return "cocheras"
    if route_index == 0:
        return "ida"
    if route_index == 1:
        return "vuelta"
    return "variante"


def _normalize_text(text: str) -> str:
    base = unicodedata.normalize("NFKD", text)
    plain = "".join(char for char in base if not unicodedata.combining(char))
    return " ".join(plain.casefold().strip().split())


def _request_headers(profile: str) -> dict[str, str]:
    if profile == "browser":
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/javascript,*/*;q=0.1",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
            "Referer": "https://itranvias.com/",
            "Origin": "https://itranvias.com",
            "Connection": "close",
        }
    return {"User-Agent": "bus-arrivals-coruna-data/1.0", "Accept": "application/json,*/*;q=0.1"}


def _http_fallback_url(url: str) -> str:
    if url.startswith("https://"):
        return "http://" + url[len("https://") :]
    return url


def _fetch_once(url: str, timeout_seconds: float, profile: str) -> str:
    request = Request(url, headers=_request_headers(profile))
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        # Some WAFs block urllib signatures. Retry once with curl keeping the same headers.
        if exc.code in (403, 429):
            return _fetch_once_curl(url=url, timeout_seconds=timeout_seconds, profile=profile)
        raise


def _fetch_once_curl(url: str, timeout_seconds: float, profile: str) -> str:
    headers = _request_headers(profile)
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--location",
        "--compressed",
        "--max-time",
        str(max(1, int(timeout_seconds))),
        "--connect-timeout",
        "5",
        "-w",
        "\n%{http_code}",
        url,
    ]
    for key, value in headers.items():
        command.extend(["-H", f"{key}: {value}"])

    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip() or "curl_failed"
        raise URLError(stderr)

    output = completed.stdout or ""
    body, separator, status_text = output.rpartition("\n")
    if not separator:
        body = output
        status_text = ""
    status_code = _safe_int(status_text.strip())
    if status_code is None:
        return body
    if 200 <= status_code < 300:
        return body

    raise HTTPError(url=url, code=status_code, msg=f"curl_http_{status_code}", hdrs=None, fp=None)


def _retry_delay_seconds(status_code: int, attempt_index: int) -> float:
    base = 0.6 if status_code == 403 else 1.0
    delay = base * (2**attempt_index)
    return min(delay, 4.0)


def fetch_json(
    url: str,
    timeout_seconds: float = 10.0,
    request_profile: str = "auto",
    retry_403: int = 1,
    allow_http_fallback: bool = True,
) -> dict[str, Any]:
    profiles: list[str]
    if request_profile == "browser":
        profiles = ["browser"]
    elif request_profile == "default":
        profiles = ["default"]
    else:
        profiles = ["default", "browser"]

    attempt_urls = [url]
    if allow_http_fallback:
        fallback = _http_fallback_url(url)
        if fallback != url:
            attempt_urls.append(fallback)

    last_error: Exception | None = None
    body: str | None = None
    for target in attempt_urls:
        for profile in profiles:
            attempts = retry_403 + 1
            for attempt_index in range(attempts):
                try:
                    body = _fetch_once(target, timeout_seconds=timeout_seconds, profile=profile)
                    break
                except HTTPError as exc:
                    last_error = exc
                    if exc.code in (403, 429) and attempt_index < attempts - 1:
                        time.sleep(_retry_delay_seconds(exc.code, attempt_index))
                        continue
                    break
                except (URLError, TimeoutError) as exc:
                    last_error = exc
                    break
            if body is not None:
                break
        if body is not None:
            break

    if body is None:
        if isinstance(last_error, HTTPError) and last_error.code == 403:
            raise BusApiError(
                "api_forbidden_403: iTranvias rechazo la solicitud (posible bloqueo por IP/antibot). "
                "Prueba --request-profile browser --retry-403 6 o ejecuta desde otra red."
            )
        raise BusApiError(f"api_unavailable: {last_error}")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BusApiError("invalid_json_payload") from exc

    if not isinstance(payload, dict):
        raise BusApiError("invalid_json_root")

    return payload


def parse_catalog_payload(payload: dict[str, Any], source_url: str) -> dict[str, Any]:
    i_tranvias = _as_dict(payload.get("iTranvias"))
    actualizacion = _as_dict(i_tranvias.get("actualizacion") if i_tranvias else None)
    raw_stops = _as_list(actualizacion.get("paradas") if actualizacion else None)
    raw_lines = _as_list(actualizacion.get("lineas") if actualizacion else None)

    lines: list[dict[str, Any]] = []
    for item in raw_lines:
        line = _as_dict(item)
        if not line:
            continue
        line_id = _safe_int(line.get("id"))
        if line_id is None:
            continue
        line_name = str(line.get("lin_comer") or line_id).strip()
        origin_name = str(line.get("nombre_orig") or "").strip()
        destination_name = str(line.get("nombre_dest") or "").strip()
        color = str(line.get("color") or "").strip()
        if color:
            color = color if color.startswith("#") else f"#{color.zfill(6)}"
        else:
            color = None

        route_variants: list[dict[str, Any]] = []
        for route_index, raw_route in enumerate(_as_list(line.get("rutas"))):
            route = _as_dict(raw_route)
            if not route:
                continue
            route_id = _safe_int(route.get("ruta"))
            direction_code = _safe_int(route.get("sentido"))
            stop_ids = []
            for raw_stop_id in _as_list(route.get("paradas")):
                parsed_stop_id = _safe_int(raw_stop_id)
                if parsed_stop_id is not None:
                    stop_ids.append(parsed_stop_id)
            route_variants.append(
                {
                    "route_id": route_id,
                    "route_index": route_index,
                    "direction_code": direction_code,
                    "direction": _infer_direction(direction_code, route_index),
                    "origin_name": str(route.get("nombre_orig") or "").strip(),
                    "destination_name": str(route.get("nombre_dest") or "").strip(),
                    "stop_ids": stop_ids,
                    "stop_count": len(stop_ids),
                }
            )

        directions = sorted(
            {
                variant["direction"]
                for variant in route_variants
                if variant.get("direction") in {"ida", "vuelta"}
            }
        )
        lines.append(
            {
                "id": line_id,
                "name": line_name,
                "commercial_name": line_name,
                "origin_name": origin_name,
                "destination_name": destination_name,
                "color_hex": color,
                "directions": directions,
                "has_ida": "ida" in directions,
                "has_vuelta": "vuelta" in directions,
                "route_variants": route_variants,
            }
        )
    lines.sort(key=lambda line: line["id"])

    stops: list[dict[str, Any]] = []
    for item in raw_stops:
        stop = _as_dict(item)
        if not stop:
            continue
        stop_id = _safe_int(stop.get("id"))
        if stop_id is None:
            continue
        line_ids = []
        for line in _as_list(stop.get("enlaces")):
            line_id = _safe_int(line)
            if line_id is not None:
                line_ids.append(line_id)
        stop_name = str(stop.get("nombre") or f"Parada {stop_id}").strip()
        stops.append(
            {
                "id": stop_id,
                "name": stop_name,
                "latitude": _safe_float(stop.get("posy")),
                "longitude": _safe_float(stop.get("posx")),
                "lines": sorted(set(line_ids)),
            }
        )
    stops.sort(key=lambda stop: stop["id"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "stops": stops,
        "lines": lines,
    }


def build_catalog_from_api(
    stops_url: str = CATALOG_URL_DEFAULT,
    timeout_seconds: float = 10.0,
    request_profile: str = "auto",
    retry_403: int = 1,
    allow_http_fallback: bool = True,
) -> dict[str, Any]:
    payload = fetch_json(
        stops_url,
        timeout_seconds=timeout_seconds,
        request_profile=request_profile,
        retry_403=retry_403,
        allow_http_fallback=allow_http_fallback,
    )
    return parse_catalog_payload(payload, source_url=stops_url)


def load_catalog(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    lines = raw.get("lines")
    stops = raw.get("stops")
    if not isinstance(lines, list) or not isinstance(stops, list):
        return None
    return raw


def save_catalog(path: Path, catalog: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_stop(
    stop_id: int | None,
    stop_name: str | None,
    catalog: dict[str, Any] | None,
) -> CatalogLookupResult:
    if stop_id is not None:
        if catalog:
            for stop in catalog.get("stops", []):
                if _safe_int(_as_dict(stop).get("id") if _as_dict(stop) else None) == stop_id:
                    return CatalogLookupResult(value=_as_dict(stop) or {"id": stop_id}, matched_by="stop_id")
        return CatalogLookupResult(
            value={"id": stop_id, "name": f"Parada {stop_id}", "lines": []},
            matched_by="stop_id",
        )

    if not stop_name:
        raise ValueError("stop_selector_required")
    if not catalog:
        raise ValueError("catalog_required_for_stop_name")

    normalized_query = _normalize_text(stop_name)
    candidates: list[dict[str, Any]] = []
    exact: list[dict[str, Any]] = []
    for raw_stop in catalog.get("stops", []):
        stop = _as_dict(raw_stop)
        if not stop:
            continue
        name = str(stop.get("name") or "")
        norm_name = _normalize_text(name)
        if normalized_query == norm_name:
            exact.append(stop)
        elif normalized_query in norm_name:
            candidates.append(stop)

    if len(exact) == 1:
        return CatalogLookupResult(value=exact[0], matched_by="stop_name_exact")
    if len(exact) > 1:
        raise ValueError("stop_name_ambiguous")
    if len(candidates) == 1:
        return CatalogLookupResult(value=candidates[0], matched_by="stop_name_contains")
    if len(candidates) > 1:
        raise ValueError("stop_name_ambiguous")
    raise ValueError("stop_not_found")


def resolve_line_id(
    line_id: int | None,
    line_name: str | None,
    catalog: dict[str, Any] | None,
) -> tuple[int | None, str | None]:
    if line_id is not None:
        return line_id, "line_id"
    if not line_name:
        return None, None
    if not catalog:
        parsed = _safe_int(line_name)
        if parsed is not None:
            return parsed, "line_name_numeric_without_catalog"
        raise ValueError("catalog_required_for_line_name")

    normalized_query = _normalize_text(line_name)
    exact: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for raw_line in catalog.get("lines", []):
        line = _as_dict(raw_line)
        if not line:
            continue
        name = str(line.get("name") or "")
        commercial_name = str(line.get("commercial_name") or name)
        line_id_value = _safe_int(line.get("id"))
        normalized_name = _normalize_text(name)
        normalized_commercial = _normalize_text(commercial_name)
        id_as_text = str(line_id_value) if line_id_value is not None else ""

        if (
            normalized_query == normalized_name
            or normalized_query == normalized_commercial
            or normalized_query == id_as_text
        ):
            exact.append(line)
        elif (
            normalized_query in normalized_name
            or normalized_query in normalized_commercial
            or (id_as_text and normalized_query in id_as_text)
        ):
            candidates.append(line)

    selected: dict[str, Any] | None = None
    if len(exact) == 1:
        selected = exact[0]
    elif len(exact) > 1:
        raise ValueError("line_name_ambiguous")
    elif len(candidates) == 1:
        selected = candidates[0]
    elif len(candidates) > 1:
        raise ValueError("line_name_ambiguous")

    if not selected:
        raise ValueError("line_not_found")

    selected_id = _safe_int(selected.get("id"))
    if selected_id is None:
        raise ValueError("line_not_found")
    return selected_id, "line_name"


def get_line_meta_map(catalog: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not catalog:
        return {}
    mapping: dict[int, dict[str, Any]] = {}
    for raw_line in catalog.get("lines", []):
        line = _as_dict(raw_line)
        if not line:
            continue
        line_id = _safe_int(line.get("id"))
        if line_id is None:
            continue
        commercial_name = str(line.get("commercial_name") or line.get("name") or line_id)
        mapping[line_id] = {
            "id": line_id,
            "name": commercial_name,
            "commercial_name": commercial_name,
            "color_hex": line.get("color_hex"),
            "directions": line.get("directions"),
            "has_ida": line.get("has_ida"),
            "has_vuelta": line.get("has_vuelta"),
        }
    return mapping


def fetch_stop_arrivals(
    stop_id: int,
    catalog: dict[str, Any] | None = None,
    arrivals_url_template: str = ARRIVALS_URL_TEMPLATE_DEFAULT,
    timeout_seconds: float = 10.0,
    request_profile: str = "auto",
    retry_403: int = 1,
    allow_http_fallback: bool = True,
) -> dict[str, Any]:
    line_meta_by_id = get_line_meta_map(catalog)
    url = arrivals_url_template.format(stop_id=stop_id)
    payload = fetch_json(
        url,
        timeout_seconds=timeout_seconds,
        request_profile=request_profile,
        retry_403=retry_403,
        allow_http_fallback=allow_http_fallback,
    )
    buses_root = _as_dict(payload.get("buses"))
    raw_lines = _as_list(buses_root.get("lineas") if buses_root else None)

    lines: list[dict[str, Any]] = []
    for raw_line in raw_lines:
        line = _as_dict(raw_line)
        if not line:
            continue
        line_id = _safe_int(line.get("linea"))
        if line_id is None:
            continue
        meta = line_meta_by_id.get(line_id) or {"id": line_id, "name": str(line_id), "color_hex": None}
        buses: list[dict[str, Any]] = []
        for raw_bus in _as_list(line.get("buses")):
            bus = _as_dict(raw_bus)
            if not bus:
                continue
            bus_id = _safe_int(bus.get("bus"))
            if bus_id is None:
                continue
            eta_minutes = _safe_int(bus.get("tiempo"))
            buses.append(
                {
                    "bus_id": bus_id,
                    "eta_minutes": eta_minutes,
                    "eta_label": format_eta(eta_minutes),
                    "distance_meters": _safe_int(bus.get("distancia")),
                    "status": _safe_int(bus.get("estado")),
                    "last_stop_id": _safe_int(bus.get("ult_parada")),
                }
            )
        buses.sort(key=lambda item: _sort_eta(_safe_int(item.get("eta_minutes"))))
        lines.append(
            {
                "line_id": line_id,
                "line_name": meta.get("name"),
                "line_commercial_name": meta.get("commercial_name"),
                "color_hex": meta.get("color_hex"),
                "directions": meta.get("directions"),
                "has_ida": meta.get("has_ida"),
                "has_vuelta": meta.get("has_vuelta"),
                "buses": buses,
            }
        )

    lines.sort(key=_first_eta_from_line)

    return {"stop_id": stop_id, "lines": lines, "api_url": url}


def find_bus(arrivals: dict[str, Any], bus_id: int) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for line in arrivals.get("lines", []):
        current_line = _as_dict(line)
        if not current_line:
            continue
        for bus in _as_list(current_line.get("buses")):
            current_bus = _as_dict(bus)
            if not current_bus:
                continue
            if _safe_int(current_bus.get("bus_id")) == bus_id:
                return current_line, current_bus
    return None


def find_line(
    arrivals: dict[str, Any],
    line_id: int | None,
) -> dict[str, Any] | None:
    if line_id is None:
        return None
    for line in arrivals.get("lines", []):
        current_line = _as_dict(line)
        if not current_line:
            continue
        if _safe_int(current_line.get("line_id")) == line_id:
            return current_line
    return None


def format_eta(eta_minutes: int | None) -> str:
    if eta_minutes is None:
        return "sin_dato"
    if eta_minutes <= 0:
        return "llegando"
    if eta_minutes == 1:
        return "1 min"
    return f"{eta_minutes} min"
