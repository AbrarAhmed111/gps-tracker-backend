from typing import Dict, Any, List, Tuple
from utils.geo_math import haversine_distance_km, calculate_bearing, calculate_speed_kmh
from datetime import datetime
import math


def calculate_route_statistics(waypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(waypoints) < 2:
        return {"total_distance_km": 0.0, "max_speed_kmh": 0.0, "average_speed_kmh": 0.0}
    total_km = 0.0
    speeds: List[float] = []
    time_hours_total = 0.0
    for i in range(1, len(waypoints)):
        p1 = waypoints[i - 1]
        p2 = waypoints[i]
        dist = haversine_distance_km(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"])
        total_km += dist
        t1: datetime = p1.get("timestamp")
        t2: datetime = p2.get("timestamp")
        if t1 and t2 and t2 > t1:
            hours = (t2 - t1).total_seconds() / 3600.0
            time_hours_total += hours
            speeds.append(calculate_speed_kmh(dist, hours))
    avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
    return {"total_distance_km": total_km, "max_speed_kmh": (max(speeds) if speeds else 0.0), "average_speed_kmh": avg_speed}


def find_route_bounds(waypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not waypoints:
        return {"northeast": None, "southwest": None, "center": None}
    lats = [w["latitude"] for w in waypoints]
    lngs = [w["longitude"] for w in waypoints]
    ne = {"latitude": max(lats), "longitude": max(lngs)}
    sw = {"latitude": min(lats), "longitude": min(lngs)}
    center = {"latitude": (ne["latitude"] + sw["latitude"]) / 2, "longitude": (ne["longitude"] + sw["longitude"]) / 2}
    return {"northeast": ne, "southwest": sw, "center": center}


def analyze_segments(waypoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    for i in range(1, len(waypoints)):
        p1 = waypoints[i - 1]
        p2 = waypoints[i]
        dist_km = haversine_distance_km(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"])
        duration_minutes = None
        speed_kmh = 0.0
        if p1.get("timestamp") and p2.get("timestamp"):
            minutes = (p2["timestamp"] - p1["timestamp"]).total_seconds() / 60.0
            duration_minutes = max(0, minutes)
            speed_kmh = calculate_speed_kmh(dist_km, (duration_minutes / 60.0))
        bearing = calculate_bearing(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"])
        segments.append({
            "segment_number": i,
            "from_sequence": int(p1.get("sequence", i)),
            "to_sequence": int(p2.get("sequence", i + 1)),
            "distance_km": round(dist_km, 3),
            "distance_m": int(dist_km * 1000),
            "duration": None,  # can be formatted "HH:MM:SS" if needed
            "duration_minutes": None if duration_minutes is None else round(duration_minutes, 2),
            "speed_kmh": round(speed_kmh, 2),
            "bearing": round(bearing, 1),
            "is_parking": bool(p2.get("is_parking", False)),
        })
    return segments


def speed_distribution(speeds: List[float]) -> Dict[str, int]:
    bins = {"0-20_kmh": 0, "20-40_kmh": 0, "40-60_kmh": 0, "60+_kmh": 0}
    for s in speeds:
        if s < 20:
            bins["0-20_kmh"] += 1
        elif s < 40:
            bins["20-40_kmh"] += 1
        elif s < 60:
            bins["40-60_kmh"] += 1
        else:
            bins["60+_kmh"] += 1
    return bins

