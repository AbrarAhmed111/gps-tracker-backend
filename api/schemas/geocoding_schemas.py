from pydantic import BaseModel, Field
from typing import Optional, List


class GeocodeRequest(BaseModel):
	address: str
	cache_key: Optional[str] = None
	language: Optional[str] = Field(default=None, description="e.g., en")
	region: Optional[str] = Field(default=None, description="e.g., pk")


class BatchGeocodeItem(BaseModel):
	id: str
	address: str
	cache_key: Optional[str] = None


class BatchGeocodeRequest(BaseModel):
	addresses: List[BatchGeocodeItem]
	language: Optional[str] = None
	region: Optional[str] = None
