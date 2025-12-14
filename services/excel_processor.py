import base64
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import pandas as pd

from utils.checksum import compute_checksum_base64, checksum_text_md5
from utils.geo_math import haversine_distance_km
from utils.validators import coordinates_valid, has_required_columns


REQUIRED_COLUMNS = ["timestamp", "day_of_week", "address"]

# We anchor all weekly routes to a synthetic, never-changing week so that
# playback is date-independent (e.g., Monday = 2024-01-01, Tuesday = 2024-01-02, etc).
ANCHOR_WEEK_START = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Monday


def read_excel_from_base64(file_content_b64: str) -> pd.DataFrame:
    data = base64.b64decode(file_content_b64)
    buffer = io.BytesIO(data)
    return pd.read_excel(buffer)


def quick_validate_excel(file_content_b64: str) -> Dict[str, Any]:
    try:
        df = read_excel_from_base64(file_content_b64)
    except Exception as e:
        return {
            "valid": False,
            "message": f"Unable to read Excel file: {e}",
            "required_columns_present": False,
        }
    cols_ok = has_required_columns(df.columns, REQUIRED_COLUMNS)
    return {
        "valid": cols_ok,
        "message": "OK" if cols_ok else "Missing required columns",
        "required_columns_present": cols_ok,
        "rows_count": int(df.shape[0]),
        "columns_found": list(df.columns),
    }


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Normalize column names
    df.columns = [str(c).strip().lower() for c in df.columns]
    # Parse timestamps
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
    # Ensure numeric lat/lng if present
    for col in ("latitude", "longitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _anchor_timestamp(ts: Optional[pd.Timestamp], day_of_week: int) -> Optional[datetime]:
    """
    Convert any provided timestamp into an anchor-week datetime so that routes
    repeat weekly without depending on real calendar dates. The date portion is
    replaced with a synthetic week (Mon Jan 1, 2024 as day 0).
    """
    if ts is None or pd.isna(ts):
        return None
    try:
        dow = int(day_of_week)
    except Exception:
        dow = 0
    dow = max(0, min(6, dow))
    dt = ts.to_pydatetime()
    anchor_base = ANCHOR_WEEK_START + timedelta(days=dow)
    return anchor_base.replace(
        hour=dt.hour,
        minute=dt.minute,
        second=dt.second,
        microsecond=dt.microsecond,
    )


def _compute_distance_stats(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    if len(rows) < 2:
        return {"total_distance_km": 0.0}
    total = 0.0
    for i in range(1, len(rows)):
        p1, p2 = rows[i - 1], rows[i]
        if coordinates_valid(p1["latitude"], p1["longitude"]) and coordinates_valid(p2["latitude"], p2["longitude"]):
            total += haversine_distance_km(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"])
    return {"total_distance_km": total}


def process_excel(file_content_b64: str, file_name: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data_bytes = base64.b64decode(file_content_b64)
    file_size_bytes = len(data_bytes)
    df = read_excel_from_base64(file_content_b64)
    df = _normalize_df(df)

    checksum = compute_checksum_base64(file_content_b64, "md5")
    rows_processed = int(df.shape[0])
    columns_found = list(df.columns)

    # Basic validation
    errors = []
    warnings = []
    required_ok = has_required_columns(df.columns, REQUIRED_COLUMNS)
    if not required_ok:
        missing = [col for col in REQUIRED_COLUMNS if col.lower() not in [c.lower() for c in df.columns]]
        errors.append({"severity": "error", "field": "columns", "message": f"Missing required columns: {', '.join(missing)}"})

    # Day handling
    has_day = "day_of_week" in df.columns
    if not has_day:
        df["day_of_week"] = 0
    days_found = sorted([int(d) for d in df["day_of_week"].dropna().unique().tolist()])
    waypoints_per_day = {str(int(d)): int((df["day_of_week"] == d).sum()) for d in days_found}

    # Date range (anchor-week) – collect anchored timestamps per row to preserve ordering across days
    anchored_ts_values: List[datetime] = []
    if "timestamp" in df.columns and df["timestamp"].notna().any():
        for _, row in df.iterrows():
            anchored_ts = _anchor_timestamp(row.get("timestamp"), row.get("day_of_week", 0))
            if anchored_ts:
                anchored_ts_values.append(anchored_ts)
    date_range = {
        "earliest": min(anchored_ts_values).isoformat() if anchored_ts_values else None,
        "latest": max(anchored_ts_values).isoformat() if anchored_ts_values else None,
        "anchor_week": True,
    }

    # Parking info
    parking_points_detected = int(df["is_parking"].sum()) if "is_parking" in df.columns else 0

    # Addresses to geocode
    addresses_need_geocoding = 0
    addresses_to_geocode: List[Dict[str, Any]] = []
    if "address" in df.columns:
        for idx, row in df.iterrows():
            lat = row.get("latitude")
            lng = row.get("longitude")
            addr = row.get("address")
            if pd.isna(lat) or pd.isna(lng):
                if isinstance(addr, str) and addr.strip():
                    addresses_need_geocoding += 1
                    addresses_to_geocode.append({
                        "sequence": int(row.get("sequence", idx + 1)),
                        "address": addr.strip(),
                        "day_of_week": int(row.get("day_of_week", 0)),
                        "cache_key": checksum_text_md5(addr.strip()),
                    })

    # Waypoints by day
    waypoints_by_day: Dict[str, List[Dict[str, Any]]] = {}
    for d in days_found:
        day_df = df[df["day_of_week"] == d].reset_index(drop=True)
        items: List[Dict[str, Any]] = []
        for i, row in day_df.iterrows():
            anchored_ts = _anchor_timestamp(row.get("timestamp"), row.get("day_of_week", d))
            items.append({
                "sequence": int(row.get("sequence", i + 1)),
                "timestamp": anchored_ts.isoformat() if anchored_ts else None,
                "day_of_week": int(row.get("day_of_week", d)),
                "latitude": float(row.get("latitude")) if pd.notna(row.get("latitude")) else None,
                "longitude": float(row.get("longitude")) if pd.notna(row.get("longitude")) else None,
                "original_address": row.get("address") if isinstance(row.get("address"), str) else None,
                "is_parking": bool(row.get("is_parking")) if "is_parking" in row else False,
                "parking_duration_minutes": int(row.get("parking_duration_minutes")) if "parking_duration_minutes" in row and pd.notna(row.get("parking_duration_minutes")) else None,
                "needs_geocoding": ("address" in df.columns and (pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")))),
                "notes": row.get("notes") if isinstance(row.get("notes"), str) else None,
            })
        waypoints_by_day[str(int(d))] = items

    # Distance statistics (overall)
    rows_for_stats: List[Dict[str, Any]] = []
    for _, row in df.sort_values(by=["timestamp"], na_position="last").iterrows():
        lat = row.get("latitude")
        lng = row.get("longitude")
        ts = _anchor_timestamp(row.get("timestamp"), row.get("day_of_week", 0))
        if pd.notna(lat) and pd.notna(lng):
            rows_for_stats.append({
                "latitude": float(lat),
                "longitude": float(lng),
                "timestamp": ts,
            })
    stats = _compute_distance_stats(rows_for_stats)

    route_summary = {
        "total_waypoints": rows_processed,
        "days_found": days_found,
        "waypoints_per_day": waypoints_per_day,
        "date_range": date_range,
        "parking_points_detected": parking_points_detected,
        "addresses_need_geocoding": addresses_need_geocoding,
    }

    validation = {
        "errors": errors,
        "warnings": warnings,
    }

    return {
        "file_info": {
            "file_name": file_name,
            "file_checksum": checksum,
            "file_size_bytes": file_size_bytes,
            "rows_processed": rows_processed,
            "rows_skipped": 0,
            "rows_with_errors": len(errors),
        },
        "route_summary": route_summary,
        "waypoints_by_day": waypoints_by_day,
        "addresses_to_geocode": addresses_to_geocode,
        "validation": validation,
        "statistics": {
            "total_distance_km": stats.get("total_distance_km", 0.0),
        },
        "columns_found": columns_found,
    }

