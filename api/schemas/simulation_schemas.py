from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WaypointInput(BaseModel):
	sequence: int = Field(..., ge=1)
	timestamp: datetime
	day_of_week: int = Field(..., ge=0, le=6)
	latitude: float = Field(..., ge=-90, le=90)
	longitude: float = Field(..., ge=-180, le=180)
	is_parking: bool = False
	original_address: Optional[str] = None


class VehiclePosition(BaseModel):
	latitude: float
	longitude: float
	timestamp: datetime
	status: Optional[str] = None
	speed_kmh: Optional[float] = None
	bearing: Optional[float] = None


class PositionRequest(BaseModel):
	vehicle_id: str
	current_time: datetime
	day_of_week: int
	is_day_active: bool
	waypoints: List[WaypointInput]
	last_known_position: Optional[VehiclePosition] = None
	interpolation_method: str = "linear"


class BatchPositionsRequest(BaseModel):
	current_time: datetime
	vehicles: List[PositionRequest]
	interpolation_method: str = "linear"
