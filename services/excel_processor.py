import base64
import io
from typing import Dict, Any, List, Optional
import pandas as pd
from utils.checksum import compute_checksum_base64, checksum_text_md5
from utils.validators import has_required_columns, coordinates_valid
from utils.geo_math import haversine_distance_km
from datetime import datetime


REQUIRED_COLUMNS = ["timestamp", "latitude", "longitude"]


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
        errors.append({"severity": "error", "field": "columns", "message": "Missing required columns"})

    # Day handling
    has_day = "day_of_week" in df.columns
    if not has_day:
        df["day_of_week"] = 0
    days_found = sorted([int(d) for d in df["day_of_week"].dropna().unique().tolist()])
    waypoints_per_day = {str(int(d)): int((df["day_of_week"] == d).sum()) for d in days_found}

    # Date range
    if "timestamp" in df.columns and df["timestamp"].notna().any():
        ts_non_null = df["timestamp"].dropna()
        date_range = {"earliest": ts_non_null.min().isoformat(), "latest": ts_non_null.max().isoformat()}
    else:
        date_range = None

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
            items.append({
                "sequence": int(row.get("sequence", i + 1)),
                "timestamp": (row["timestamp"].isoformat() if isinstance(row.get("timestamp"), pd.Timestamp) and pd.notna(row.get("timestamp")) else None),
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
        ts = row.get("timestamp")
        if pd.notna(lat) and pd.notna(lng):
            rows_for_stats.append({
                "latitude": float(lat),
                "longitude": float(lng),
                "timestamp": ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else None,
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

