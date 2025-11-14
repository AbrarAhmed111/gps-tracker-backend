from typing import Iterable


def coordinates_valid(lat: float, lng: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


def has_required_columns(columns: Iterable[str], required: Iterable[str]) -> bool:
    cols = set(c.lower() for c in columns)
    return all(r.lower() in cols for r in required)

