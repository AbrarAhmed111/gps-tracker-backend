from typing import List, Dict
from pydantic import BaseModel, Field, conint
from fastapi import APIRouter, HTTPException

from services.ai import generate_fibonacci, count_words, normalize_numbers

router = APIRouter(prefix="/ai", tags=["ai"])


class FibonacciRequest(BaseModel):
    count: conint(ge=0, le=10000) = Field(..., description="Number of Fibonacci terms")


class FibonacciResponse(BaseModel):
    sequence: List[int]


@router.post("/fibonacci", response_model=FibonacciResponse)
async def fibonacci(req: FibonacciRequest):
    try:
        seq = generate_fibonacci(req.count)
        return FibonacciResponse(sequence=seq)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class WordCountRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to analyze")


class WordCountResponse(BaseModel):
    counts: Dict[str, int]
    total_words: int
    unique_words: int


@router.post("/wordcount", response_model=WordCountResponse)
async def wordcount(req: WordCountRequest):
    counts = count_words(req.text)
    total = sum(counts.values())
    unique = len(counts)
    return WordCountResponse(counts=counts, total_words=total, unique_words=unique)


class NormalizeRequest(BaseModel):
    values: List[float] = Field(..., description="Array of numbers")


class NormalizeResponse(BaseModel):
    normalized: List[float]


@router.post("/normalize", response_model=NormalizeResponse)
async def normalize(req: NormalizeRequest):
    normalized_values = normalize_numbers(req.values)
    return NormalizeResponse(normalized=normalized_values)

