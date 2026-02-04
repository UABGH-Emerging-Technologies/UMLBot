"""Pydantic schemas for v01 API endpoints."""

from typing import Any, List, Optional

from pydantic import BaseModel


class ExampleRequest(BaseModel):
    """Payload schema for example categorization requests."""
    unique_ids: Optional[List[str]] = None
    text_to_label: List[str]
