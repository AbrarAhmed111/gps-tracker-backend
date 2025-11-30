from fastapi import APIRouter, HTTPException
from api.schemas.geocoding_schemas import GeocodeRequest, BatchGeocodeRequest
import requests
import os
from typing import Dict, Any, List

router = APIRouter(prefix="/v1/geocoding", tags=["geocoding"])


@router.post("/geocode")
async def geocode(req: GeocodeRequest):
    """Geocode a single address using Google Maps API."""
    if not req.api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": req.address,
            "key": req.api_key,
        }
        if req.language:
            params["language"] = req.language
        if req.region:
            params["region"] = req.region
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Geocoding failed: {data.get('status')}")
        
        result = data.get("results", [{}])[0]
        location = result.get("geometry", {}).get("location", {})
        
        return {
            "success": True,
            "data": {
                "latitude": location.get("lat"),
                "longitude": location.get("lng"),
                "formatted_address": result.get("formatted_address"),
                "raw": result,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")


@router.post("/batch")
async def batch_geocode(req: BatchGeocodeRequest):
    """Geocode multiple addresses in batch."""
    if not req.api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    results: List[Dict[str, Any]] = []
    
    for item in req.addresses:
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": item.address,
                "key": req.api_key,
            }
            if req.language:
                params["language"] = req.language
            if req.region:
                params["region"] = req.region
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status")
            if status == "OK":
                result = data.get("results", [{}])[0]
                if not result:
                    results.append({
                        "id": item.id,
                        "success": False,
                        "error": "No results returned",
                        "address": item.address,
                    })
                else:
                    location = result.get("geometry", {}).get("location", {})
                    if not location or "lat" not in location or "lng" not in location:
                        results.append({
                            "id": item.id,
                            "success": False,
                            "error": "Invalid location data",
                            "address": item.address,
                        })
                    else:
                        results.append({
                            "id": item.id,
                            "success": True,
                            "latitude": location.get("lat"),
                            "longitude": location.get("lng"),
                            "formatted_address": result.get("formatted_address"),
                            "raw": result,
                            "address": item.address,
                        })
            else:
                # Provide more detailed error messages
                error_msg = status
                if status == "ZERO_RESULTS":
                    error_msg = "Address not found - please check spelling and completeness"
                elif status == "OVER_QUERY_LIMIT":
                    error_msg = "Geocoding API quota exceeded"
                elif status == "REQUEST_DENIED":
                    error_msg = "Geocoding API access denied - check API key permissions"
                elif status == "INVALID_REQUEST":
                    error_msg = "Invalid address format"
                
                results.append({
                    "id": item.id,
                    "success": False,
                    "error": error_msg,
                    "status": status,
                    "address": item.address,
                })
        except Exception as e:
            results.append({
                "id": item.id,
                "success": False,
                "error": str(e),
            })
    
    return {
        "success": True,
        "data": {
            "results": results,
            "total": len(results),
            "successful": sum(1 for r in results if r.get("success")),
        }
    }

