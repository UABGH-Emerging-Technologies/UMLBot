"""Example v01 endpoint implementations."""

from fastapi import APIRouter, HTTPException

from app.fastapi_config import EXAMPLE_META
from app.v01.schemas import ExampleRequest

router = APIRouter(tags=["examples"])


@router.post("/cv/v01/labels/single", **EXAMPLE_META)
async def process_categorize(request: ExampleRequest) -> dict[str, list[str]]:
    """Stub endpoint for categorization requests."""
    if not request.text_to_label:
        raise HTTPException(status_code=400, detail="text_to_label must not be empty.")
    return {"labels": ["unimplemented" for _ in request.text_to_label]}
