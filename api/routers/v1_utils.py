from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from utils.checksum import compute_checksum_base64


router = APIRouter(prefix="/v1/utils", tags=["utils"])


class ChecksumRequest(BaseModel):
    file_content: str = Field(..., description="Base64-encoded file")
    algorithm: str = Field(default="sha256", description="md5 | sha1 | sha256")


@router.post("/checksum")
async def checksum(req: ChecksumRequest):
    try:
        value = compute_checksum_base64(req.file_content, req.algorithm)  # type: ignore[arg-type]
        return {"success": True, "checksum": value, "algorithm": req.algorithm}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

