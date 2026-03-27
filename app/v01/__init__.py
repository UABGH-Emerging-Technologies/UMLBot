"""v01 API version — aggregates sub-routers."""

from fastapi import APIRouter

from app.v01.config_router import router as config_router
from app.v01.generate import router as generate_router
from app.v01.render import router as render_router

v01_router = APIRouter()
v01_router.include_router(generate_router)
v01_router.include_router(render_router)
v01_router.include_router(config_router)

__all__ = ["v01_router"]
