from fastapi import APIRouter, HTTPException
from api.schemas.excel_schemas import ExcelProcessRequest, ExcelValidateRequest
from services.excel_processor import process_excel, quick_validate_excel
import time


router = APIRouter(prefix="/v1/excel", tags=["excel"])


@router.post("/process")
async def process(req: ExcelProcessRequest):
    start = time.time()
    try:
        result = process_excel(req.file_content, req.file_name, req.options.model_dump() if req.options else None)
        return {
            "success": True,
            "message": "Excel file processed successfully",
            "processing_time_ms": int((time.time() - start) * 1000),
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to process Excel: {e}")


@router.post("/validate")
async def validate(req: ExcelValidateRequest):
    start = time.time()
    result = quick_validate_excel(req.file_content)
    return {
        "success": True,
        "validation_time_ms": int((time.time() - start) * 1000),
        **result,
    }

