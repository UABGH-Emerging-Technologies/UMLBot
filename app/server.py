"""FastAPI entry point for UMLBot."""

import os

import uvicorn
from fastapi import FastAPI

from app.fastapi_config import (
    API_CONTACT,
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
)
from app.v01 import v01_router

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    contact=API_CONTACT,
    root_path=os.environ.get("ROOT_PATH", ""),
)

app.include_router(v01_router, prefix="/v01")


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
