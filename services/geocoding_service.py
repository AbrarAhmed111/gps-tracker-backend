import json
import logging
import os
from typing import Optional, Dict, Any, List

import googlemaps
import httpx

from utils.checksum import checksum_text_md5

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else None
CACHE_TIMEOUT = float(os.getenv("GEOCODE_CACHE_TIMEOUT_SECONDS", "5.0"))


def _cache_enabled() -> bool:
    return bool(SUPABASE_REST_URL and SUPABASE_SERVICE_ROLE_KEY)


def _normalize_address(address: str) -> str:
    return " ".join(address.strip().split()).lower()


def _address_hash(address: str) -> str:
    return checksum_text_md5(_normalize_address(address))


def _supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _fetch_cached_entry(address: str) -> Optional[Dict[str, Any]]:
    if not _cache_enabled():
        return None
    address_hash = _address_hash(address)
    url = f"{SUPABASE_REST_URL}/geocode_cache"
    params = {
        "address_hash": f"eq.{address_hash}",
        "select": "address,latitude,longitude,formatted_address,raw,use_count",
        "limit": 1,
    }
    try:
        resp = httpx.get(url, params=params, headers=_supabase_headers(), timeout=CACHE_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        row = data[0]
        try:
            lat = float(row["latitude"])
            lng = float(row["longitude"])
        except (ValueError, TypeError):
            return None
        raw_payload = row.get("raw") or {}
        # Bump use count asynchronously (best effort)
        try:
            current_use = int(row.get("use_count") or 1) + 1
            httpx.patch(
                url,
                params={"address_hash": f"eq.{address_hash}"},
                headers=_supabase_headers(),
                json={"use_count": current_use},
                timeout=CACHE_TIMEOUT,
            )
        except Exception as exc:  # pragma: no cover - non-critical
            logger.debug("Failed to update geocode cache use_count: %s", exc)
        return {
            "success": True,
            "latitude": lat,
            "longitude": lng,
            "formatted_address": row.get("formatted_address"),
            "place_id": (raw_payload or {}).get("place_id"),
            "raw": raw_payload,
            "cached": True,
        }
    except Exception as exc:
        logger.debug("Geocode cache lookup failed: %s", exc)
        return None


def _cache_response(address: str, payload: Dict[str, Any]) -> None:
    if not _cache_enabled() or not payload.get("success"):
        return
    address_hash = _address_hash(address)
    url = f"{SUPABASE_REST_URL}/geocode_cache"
    row = {
        "address": address.strip(),
        "address_hash": address_hash,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "formatted_address": payload.get("formatted_address"),
        "raw": payload.get("raw"),
    }
    headers = _supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"
    try:
        httpx.post(url, json=row, headers=headers, timeout=CACHE_TIMEOUT)
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("Failed to write geocode cache: %s", exc)


def _geocode_via_google(client: googlemaps.Client, address: str, language: Optional[str], region: Optional[str]) -> Optional[Dict[str, Any]]:
    result = client.geocode(address, language=language, region=region)
    if not result:
        return None
    r0 = result[0]
    loc = r0["geometry"]["location"]
    return {
        "success": True,
        "latitude": loc["lat"],
        "longitude": loc["lng"],
        "formatted_address": r0.get("formatted_address"),
        "place_id": r0.get("place_id"),
        "raw": r0,
    }


def geocode_address(address: str, api_key: str, language: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    cached = _fetch_cached_entry(address)
    if cached:
        return cached
    client = googlemaps.Client(key=api_key)
    payload = _geocode_via_google(client, address, language, region)
    if not payload:
        return {"success": False, "reason": "ZERO_RESULTS"}
    _cache_response(address, payload)
    payload["cached"] = False
    return payload


def batch_geocode(addresses: List[Dict[str, Any]], api_key: str, language: Optional[str] = None, region: Optional[str] = None) -> List[Dict[str, Any]]:
    client = googlemaps.Client(key=api_key)
    results: List[Dict[str, Any]] = []
    for item in addresses:
        raw_address = (item.get("address") or "").strip()
        cache_hit = _fetch_cached_entry(raw_address)
        if cache_hit:
            results.append({
                "id": item.get("id"),
                "success": True,
                "latitude": cache_hit["latitude"],
                "longitude": cache_hit["longitude"],
                "formatted_address": cache_hit.get("formatted_address"),
                "cached": True,
            })
            continue
        payload = _geocode_via_google(client, raw_address, language, region)
        if not payload:
            results.append({"id": item.get("id"), "success": False, "reason": "ZERO_RESULTS"})
            continue
        _cache_response(raw_address, payload)
        results.append({
            "id": item.get("id"),
            "success": True,
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "formatted_address": payload.get("formatted_address"),
            "cached": False,
        })
    return results

