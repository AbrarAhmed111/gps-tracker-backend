from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from utils.geo_math import haversine_distance_km, calculate_bearing, calculate_speed_kmh, heading_from_bearing
from services.interpolation_service import linear_interpolation


def _find_current_segment(waypoints: List[Dict[str, Any]], current_time: datetime) -> Optional[Tuple[int, Dict[str, Any], Dict[str, Any], float]]:
    # Returns (index, from_wp, to_wp, progress 0..1) or None
    sorted_wps = sorted(waypoints, key=lambda w: w["timestamp"])
    for i in range(len(sorted_wps) - 1):
        w1 = sorted_wps[i]
        w2 = sorted_wps[i + 1]
        t1 = w1.get("timestamp")
        t2 = w2.get("timestamp")
        if not t1 or not t2:
            continue
        if t1 <= current_time <= t2:
            total = (t2 - t1).total_seconds()
            elapsed = (current_time - t1).total_seconds()
            progress = 0.0 if total <= 0 else max(0.0, min(1.0, elapsed / total))
            return i, w1, w2, progress
    return None


def _interpolate_position(w1: Dict[str, Any], w2: Dict[str, Any], progress: float) -> Dict[str, float]:
    lat = linear_interpolation(w1["latitude"], w2["latitude"], progress)
    lng = linear_interpolation(w1["longitude"], w2["longitude"], progress)
    return {"latitude": lat, "longitude": lng}


def simulate_position(waypoints: List[Dict[str, Any]], current_time: datetime) -> Dict[str, Any]:
    if not waypoints:
        return {"status": "inactive"}
    waypoints = [w for w in waypoints if w.get("timestamp") is not None]
    if not waypoints:
        return {"status": "inactive"}
    sorted_wps = sorted(waypoints, key=lambda w: w["timestamp"])
    first, last = sorted_wps[0], sorted_wps[-1]

    if current_time < first["timestamp"]:
        return {
            "status": "not_started",
            "position": {"latitude": first["latitude"], "longitude": first["longitude"]},
            "message": "Route not started",
        }
    if current_time > last["timestamp"]:
        return {
            "status": "completed",
            "position": {"latitude": last["latitude"], "longitude": last["longitude"]},
            "message": "Route completed",
        }

    seg = _find_current_segment(sorted_wps, current_time)
    if not seg:
        # Fallback
        return {
            "status": "inactive",
            "position": {"latitude": first["latitude"], "longitude": first["longitude"]},
        }
    idx, w1, w2, progress = seg
    pos = _interpolate_position(w1, w2, progress)
    distance_km = haversine_distance_km(w1["latitude"], w1["longitude"], w2["latitude"], w2["longitude"])
    hours = (w2["timestamp"] - w1["timestamp"]).total_seconds() / 3600.0
    speed_kmh = calculate_speed_kmh(distance_km, hours)
    bearing = calculate_bearing(w1["latitude"], w1["longitude"], w2["latitude"], w2["longitude"])
    heading = heading_from_bearing(bearing)

    overall_progress = (idx + progress) / max(1, len(sorted_wps) - 1) * 100.0
    completed_waypoints = idx
    total_waypoints = len(sorted_wps)
    remaining_waypoints = max(0, total_waypoints - completed_waypoints)

    return {
        "status": "moving" if speed_kmh > 0 else "parked",
        "position": pos,
        "movement_data": {
            "speed_kmh": round(speed_kmh, 2),
            "speed_ms": round(speed_kmh / 3.6, 2),
            "bearing": round(bearing, 1),
            "heading": heading,
            "is_accelerating": False,
            "is_decelerating": False,
        },
        "route_progress": {
            "current_segment": {
                "from_waypoint_sequence": int(w1.get("sequence", idx + 1)),
                "to_waypoint_sequence": int(w2.get("sequence", idx + 2)),
                "segment_progress_percent": round(progress * 100.0, 2),
                "from_position": {"latitude": w1["latitude"], "longitude": w1["longitude"], "timestamp": w1["timestamp"].isoformat()},
                "to_position": {"latitude": w2["latitude"], "longitude": w2["longitude"], "timestamp": w2["timestamp"].isoformat()},
            },
            "overall_progress_percent": round(overall_progress, 2),
            "completed_waypoints": completed_waypoints,
            "total_waypoints": total_waypoints,
            "remaining_waypoints": remaining_waypoints,
        },
        "eta": {
            "next_waypoint": w2["timestamp"].isoformat(),
            "final_destination": last["timestamp"].isoformat(),
            "minutes_to_next_waypoint": round((w2["timestamp"] - current_time).total_seconds() / 60.0, 2),
            "minutes_to_destination": round((last["timestamp"] - current_time).total_seconds() / 60.0, 2),
        },
        "distance": {
            "to_next_waypoint_km": round(distance_km * (1 - progress), 3),
            "to_next_waypoint_m": int(distance_km * 1000 * (1 - progress)),
            "total_remaining_km": None,
            "total_completed_km": None,
        },
    }

