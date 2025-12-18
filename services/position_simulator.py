from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import googlemaps
from googlemaps.convert import decode_polyline
from utils.geo_math import haversine_distance_km, calculate_bearing, calculate_speed_kmh, heading_from_bearing
from services.interpolation_service import linear_interpolation

_gmaps_clients: Dict[str, googlemaps.Client] = {}


def _get_gmaps_client(api_key: str) -> googlemaps.Client:
    client = _gmaps_clients.get(api_key)
    if client is None:
        client = googlemaps.Client(key=api_key)
        _gmaps_clients[api_key] = client
    return client


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


def _road_path(w1: Dict[str, Any], w2: Dict[str, Any], api_key: Optional[str]) -> Optional[List[Dict[str, float]]]:
    if not api_key:
        return None
    try:
        client = _get_gmaps_client(api_key)
        resp = client.directions(
            (w1["latitude"], w1["longitude"]),
            (w2["latitude"], w2["longitude"]),
            mode="driving",
            alternatives=False,
            departure_time=w1.get("timestamp"),
        )
        if not resp:
            return None
        # Prefer full step geometry if available, otherwise fallback to overview polyline
        route = resp[0]
        path_points: List[Dict[str, float]] = []
        legs = route.get("legs") or []
        for leg in legs:
            steps = leg.get("steps") or []
            for step in steps:
                step_poly = step.get("polyline", {})
                pts = step_poly.get("points")
                if not pts:
                    continue
                decoded_step = decode_polyline(pts)
                for p in decoded_step:
                    path_points.append({"latitude": p["lat"], "longitude": p["lng"]})
        if not path_points:
            overview = route.get("overview_polyline", {})
            pts = overview.get("points")
            if not pts:
                return None
            decoded = decode_polyline(pts)
            if not decoded:
                return None
            path_points = [{"latitude": p["lat"], "longitude": p["lng"]} for p in decoded]
        return path_points if path_points else None
    except Exception:
        return None


def _position_along_path(path: List[Dict[str, float]], progress: float) -> Tuple[Dict[str, float], float, float]:
    if len(path) < 2:
        last = path[-1] if path else {"latitude": 0.0, "longitude": 0.0}
        return last, 0.0, 0.0
    segments: List[Tuple[float, Dict[str, float], Dict[str, float]]] = []
    total_distance = 0.0
    for i in range(1, len(path)):
        start = path[i - 1]
        end = path[i]
        dist = haversine_distance_km(start["latitude"], start["longitude"], end["latitude"], end["longitude"])
        segments.append((dist, start, end))
        total_distance += dist
    if total_distance <= 0:
        last = path[-1]
        return last, 0.0, 0.0
    target_distance = max(0.0, min(1.0, progress)) * total_distance
    traveled = 0.0
    current_position = path[0]
    for dist, start, end in segments:
        if dist <= 0:
            current_position = end
            continue
        if traveled + dist >= target_distance:
            ratio = (target_distance - traveled) / dist
            lat = start["latitude"] + (end["latitude"] - start["latitude"]) * ratio
            lng = start["longitude"] + (end["longitude"] - start["longitude"]) * ratio
            current_position = {"latitude": lat, "longitude": lng}
            return current_position, total_distance, traveled + ratio * dist
        traveled += dist
        current_position = end
    return current_position, total_distance, total_distance


def simulate_position(waypoints: List[Dict[str, Any]], current_time: datetime, api_key: Optional[str] = None) -> Dict[str, Any]:
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
    pos = None
    distance_km = None
    distance_completed_km = None
    road_path = _road_path(w1, w2, api_key)
    if road_path:
        pos, distance_km, distance_completed_km = _position_along_path(road_path, progress)
    if pos is None:
        pos = _interpolate_position(w1, w2, progress)
    if distance_km is None or distance_km <= 0:
        distance_km = haversine_distance_km(w1["latitude"], w1["longitude"], w2["latitude"], w2["longitude"])
    if distance_completed_km is None:
        distance_completed_km = distance_km * progress
    segment_seconds = (w2["timestamp"] - w1["timestamp"]).total_seconds()
    hours = segment_seconds / 3600.0 if segment_seconds else 0
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
                "segment_distance_km": round(distance_km, 5),
                "segment_duration_seconds": segment_seconds,
                "road_path": road_path or None,
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
            "seconds_to_next_waypoint": round((w2["timestamp"] - current_time).total_seconds(), 2),
        },
        "distance": {
            "to_next_waypoint_km": round(max(distance_km - distance_completed_km, 0.0), 3),
            "to_next_waypoint_m": int(max(distance_km - distance_completed_km, 0.0) * 1000),
            "total_remaining_km": None,
            "total_completed_km": None,
        },
    }

