from fastapi import APIRouter
from api.schemas.simulation_schemas import PositionRequest, BatchPositionsRequest
from services.position_simulator import simulate_position
import time
from datetime import datetime, timezone, timedelta


router = APIRouter(prefix="/v1/simulation", tags=["simulation"])


ANCHOR_MONDAY = datetime(2024, 1, 1, 0, 0, 0)  # Monday anchor; only time + weekday matter


def _anchor_current_time(current_time: datetime, day_of_week: int) -> datetime:
    """Map the provided current time onto a fixed reference week so routes repeat weekly."""
    base = ANCHOR_MONDAY + timedelta(days=int(day_of_week or 0))
    return base.replace(
        hour=current_time.hour,
        minute=current_time.minute,
        second=current_time.second,
        microsecond=current_time.microsecond,
        tzinfo=current_time.tzinfo,
    )


@router.post("/calculate-position")
async def calculate_position(req: PositionRequest):
    start = time.time()
    waypoints = [w.model_dump() for w in req.waypoints]
    anchored_now = _anchor_current_time(req.current_time, req.day_of_week)
    result = simulate_position(waypoints, anchored_now, api_key=req.api_key)
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
        anchored_now = _anchor_current_time(v.current_time, v.day_of_week)
        outputs.append({
            "vehicle_id": v.vehicle_id,
            **simulate_position(waypoints, anchored_now, api_key=v.api_key or req.api_key),
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

