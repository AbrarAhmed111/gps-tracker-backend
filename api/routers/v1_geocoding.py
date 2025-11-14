from fastapi import APIRouter, HTTPException
from api.schemas.geocoding_schemas import GeocodeRequest, BatchGeocodeRequest
from services.geocoding_service import geocode_address, batch_geocode
import os
import time


router = APIRouter(prefix="/v1/geocoding", tags=["geocoding"])


@router.post("/geocode")
async def geocode(req: GeocodeRequest):
    start = time.time()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    result = geocode_address(req.address, api_key, req.language, req.region)
    elapsed = int((time.time() - start) * 1000)
    if not result.get("success"):
        return {
            "success": False,
            "error": {
                "code": "ADDRESS_NOT_FOUND",
                "message": "Unable to geocode address",
                "details": result.get("reason", "ZERO_RESULTS"),
                "original_address": req.address,
            },
        }
    raw = result.get("raw", {})
    components = raw.get("address_components", [])
    comp_map = {}
    for c in components:
        types = c.get("types", [])
        if "locality" in types:
            comp_map["city"] = c.get("long_name")
        if "administrative_area_level_1" in types:
            comp_map["state"] = c.get("long_name")
        if "country" in types:
            comp_map["country"] = c.get("long_name")
            comp_map["country_code"] = c.get("short_name")
        if "postal_code" in types:
            comp_map["postal_code"] = c.get("long_name")
        if "route" in types or "street_address" in types or "premise" in types:
            comp_map["street"] = c.get("long_name")
    viewport = raw.get("geometry", {}).get("viewport", {})
    location_type = raw.get("geometry", {}).get("location_type", "APPROXIMATE")
    return {
        "success": True,
        "cached": False,
        "api_call_made": True,
        "processing_time_ms": elapsed,
        "data": {
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "formatted_address": result.get("formatted_address"),
            "place_id": result.get("place_id"),
            "address_components": comp_map,
            "location_type": location_type,
            "viewport": viewport,
        },
        "cache_info": {
            "cache_key": None,
            "should_cache": True,
        },
    }


@router.post("/batch")
async def batch(req: BatchGeocodeRequest):
    start = time.time()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    items = [item.model_dump() for item in req.addresses]
    results = batch_geocode(items, api_key, req.language, req.region)
    elapsed = int((time.time() - start) * 1000)
    success_count = sum(1 for r in results if r.get("success"))
    failed_count = len(results) - success_count
    from_cache = sum(1 for r in results if r.get("cached"))
    return {
        "success": True,
        "processing_time_ms": elapsed,
        "summary": {
            "total_requested": len(items),
            "successfully_geocoded": success_count,
            "from_cache": from_cache,
            "from_api": success_count - from_cache,
            "failed": failed_count,
            "total_api_calls": len(items) - from_cache,
        },
        "results": results,
        "failed": [r for r in results if not r.get("success")],
        "cache_recommendations": [],
    }

