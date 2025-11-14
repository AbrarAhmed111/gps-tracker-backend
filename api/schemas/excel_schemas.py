from pydantic import BaseModel, Field
from typing import Optional, Dict


class ExcelProcessOptions(BaseModel):
	# Optional processing options; extend as needed
	detect_parking: bool = False
	parking_threshold_minutes: int = 15
	validate_coordinates: bool = True
	timezone: str = "UTC"


class ExcelProcessRequest(BaseModel):
	file_content: str = Field(..., description="Base64-encoded Excel file content")
	file_name: str = Field(..., description="Original file name")
	vehicle_id: Optional[str] = None
	options: Optional[ExcelProcessOptions] = None


class ExcelValidateRequest(BaseModel):
	file_content: str
	file_name: str
	strict_mode: bool = False
