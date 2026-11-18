import math
import threading
import time

import requests
from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

routing_bp = Blueprint("routing", __name__)
_ROUTE_CACHE = {}
_ADDRESS_CACHE = {}
_ADDRESS_LOCK = threading.Lock()
_LAST_ADDRESS_SEARCH = 0.0


def _parse_coordinate(value, minimum, maximum):
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not minimum <= number <= maximum:
        return None
    return number


def fetch_route(start_lat, start_lng, end_lat, end_lng):
    base_url = str(current_app.config.get("OSRM_API") or "").strip().rstrip("/")
    if not base_url:
        return None

    cache_key = (
        base_url,
        round(start_lat, 6),
        round(start_lng, 6),
        round(end_lat, 6),
        round(end_lng, 6),
    )
    cached = _ROUTE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    coordinates = f"{start_lng:.7f},{start_lat:.7f};{end_lng:.7f},{end_lat:.7f}"
    try:
        response = requests.get(
            f"{base_url}/{coordinates}",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
                "alternatives": "false",
            },
            headers={"User-Agent": "OneGov-PH/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes") or []
        if not routes:
            return None

        geometry = routes[0].get("geometry") or {}
        raw_coordinates = (
            geometry.get("coordinates")
            if geometry.get("type") in {"GeoJSON", "LineString"}
            else None
        )
        if not isinstance(raw_coordinates, list):
            return None

        coordinates_out = []
        for pair in raw_coordinates:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            try:
                lat = float(pair[1])
                lng = float(pair[0])
            except (TypeError, ValueError):
                continue
            if math.isfinite(lat) and math.isfinite(lng):
                coordinates_out.append([lat, lng])

        if len(coordinates_out) < 2:
            return None

        result = {
            "coordinates": coordinates_out,
            "distance": routes[0].get("distance"),
            "duration": routes[0].get("duration"),
        }
        if len(_ROUTE_CACHE) > 200:
            _ROUTE_CACHE.clear()
        _ROUTE_CACHE[cache_key] = result
        return result
    except requests.RequestException as exc:
        current_app.logger.warning("OSRM routing request failed: %s", exc)
        return None
    except (ValueError, TypeError, KeyError) as exc:
        current_app.logger.warning("OSRM routing response could not be read: %s", exc)
        return None


@routing_bp.get("/api/delivery-route")
@login_required
def delivery_route():
    start_lat = _parse_coordinate(request.args.get("start_lat"), -90, 90)
    start_lng = _parse_coordinate(request.args.get("start_lng"), -180, 180)
    end_lat = _parse_coordinate(request.args.get("end_lat"), -90, 90)
    end_lng = _parse_coordinate(request.args.get("end_lng"), -180, 180)
    if None in (start_lat, start_lng, end_lat, end_lng):
        return jsonify({"error": "Invalid route coordinates."}), 400
    if not str(current_app.config.get("OSRM_API") or "").strip():
        return jsonify({"error": "Routing service is not configured."}), 503

    result = fetch_route(start_lat, start_lng, end_lat, end_lng)
    if result is None:
        return jsonify({"error": "Routing service is unavailable."}), 502
    return jsonify(result)


def _short_address_label(item, fallback):
    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    area = next(
        (
            str(address.get(key) or "").strip()
            for key in ("suburb", "quarter", "neighbourhood", "village", "barangay")
            if str(address.get(key) or "").strip()
        ),
        "",
    )
    city = next(
        (
            str(address.get(key) or "").strip()
            for key in ("city", "town", "municipality", "county")
            if str(address.get(key) or "").strip()
        ),
        "",
    )
    parts = []
    for value in (
        str(item.get("name") or "").strip(),
        str(address.get("road") or "").strip(),
        area,
        city,
        str(address.get("state") or "").strip(),
    ):
        if value and value.casefold() not in {part.casefold() for part in parts}:
            parts.append(value)
    return ", ".join(parts) or str(item.get("display_name") or fallback).strip()


@routing_bp.get("/api/address-search")
@login_required
def address_search():
    query = str(request.args.get("q") or "").strip()[:200]
    if len(query) < 3:
        return jsonify({"error": "Enter at least 3 characters."}), 400

    base_url = str(current_app.config.get("NOMINATIM_API") or "").strip().rstrip("/")
    if not base_url:
        return jsonify({"error": "Address search is not configured."}), 503

    cache_key = (base_url, query.casefold())
    cached = _ADDRESS_CACHE.get(cache_key)
    if cached is not None:
        return jsonify(cached)

    global _LAST_ADDRESS_SEARCH
    try:
        with _ADDRESS_LOCK:
            wait = 1.0 - (time.monotonic() - _LAST_ADDRESS_SEARCH)
            if wait > 0:
                time.sleep(wait)
            _LAST_ADDRESS_SEARCH = time.monotonic()
        response = requests.get(
            base_url,
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 5,
                "countrycodes": "ph",
                "accept-language": "en",
            },
            headers={"User-Agent": "OneGov-PH/1.0 (address search prototype)"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return jsonify({"error": "Address search returned invalid data."}), 502

        results = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            lat = _parse_coordinate(item.get("lat"), -90, 90)
            lng = _parse_coordinate(item.get("lon"), -180, 180)
            if lat is None or lng is None:
                continue
            address = item.get("address") if isinstance(item.get("address"), dict) else {}
            results.append(
                {
                    "label": _short_address_label(item, query),
                    "display_name": str(item.get("display_name") or "").strip(),
                    "name": str(item.get("name") or "").strip(),
                    "lat": lat,
                    "lng": lng,
                    "address": {
                        str(key): str(value)
                        for key, value in address.items()
                        if isinstance(value, (str, int, float))
                    },
                }
            )

        output = {"results": results}
        if len(_ADDRESS_CACHE) > 200:
            _ADDRESS_CACHE.clear()
        _ADDRESS_CACHE[cache_key] = output
        return jsonify(output)
    except requests.RequestException as exc:
        current_app.logger.warning("Nominatim address search failed: %s", exc)
        return jsonify({"error": "Address search is unavailable."}), 502
    except (ValueError, TypeError, KeyError) as exc:
        current_app.logger.warning("Nominatim address search response could not be read: %s", exc)
        return jsonify({"error": "Address search returned invalid data."}), 502
