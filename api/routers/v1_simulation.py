from fastapi import APIRouter
from api.schemas.simulation_schemas import PositionRequest, BatchPositionsRequest
from services.position_simulator import simulate_position
import time
from datetime import datetime, timezone


router = APIRouter(prefix="/v1/simulation", tags=["simulation"])


@router.post("/calculate-position")
async def calculate_position(req: PositionRequest):
    start = time.time()
    waypoints = [w.model_dump() for w in req.waypoints]
    result = simulate_position(waypoints, req.current_time, api_key=req.api_key)
    return {
        "success": True,
        "processing_time_ms": int((time.time() - start) * 1000),
        "vehicle_id": req.vehicle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **result,
    }


@router.post("/calculate-positions-batch")
async def calculate_positions_batch(req: BatchPositionsRequest):
    start = time.time()
    outputs = []
    for v in req.vehicles:
        waypoints = [w.model_dump() for w in v.waypoints]
        outputs.append({
            "vehicle_id": v.vehicle_id,
            **simulate_position(waypoints, v.current_time, api_key=v.api_key or req.api_key),
        })
    summary = {
        "moving": sum(1 for o in outputs if o.get("status") == "moving"),
        "parked": sum(1 for o in outputs if o.get("status") == "parked"),
        "inactive": sum(1 for o in outputs if o.get("status") == "inactive"),
        "not_started": sum(1 for o in outputs if o.get("status") == "not_started"),
        "completed": sum(1 for o in outputs if o.get("status") == "completed"),
        "errors": 0,
    }
    return {
        "success": True,
        "processing_time_ms": int((time.time() - start) * 1000),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "positions": outputs,
        "total_vehicles": len(outputs),
        "summary": summary,
    }

