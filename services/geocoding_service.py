from typing import Optional, Dict, Any, List
import googlemaps


def geocode_address(address: str, api_key: str, language: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = googlemaps.Client(key=api_key)
    result = client.geocode(address, language=language, region=region)
    if not result:
        return {"success": False, "reason": "ZERO_RESULTS"}
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


def batch_geocode(addresses: List[Dict[str, Any]], api_key: str, language: Optional[str] = None, region: Optional[str] = None) -> List[Dict[str, Any]]:
    client = googlemaps.Client(key=api_key)
    results: List[Dict[str, Any]] = []
    for item in addresses:
        res = client.geocode(item["address"], language=language, region=region)
        if not res:
            results.append({"id": item.get("id"), "success": False, "reason": "ZERO_RESULTS"})
            continue
        r0 = res[0]
        loc = r0["geometry"]["location"]
        results.append({
            "id": item.get("id"),
            "success": True,
            "latitude": loc["lat"],
            "longitude": loc["lng"],
            "formatted_address": r0.get("formatted_address"),
        })
    return results

