# backend/routers/__init__.py

from routers.auth import router as auth_router
from routers.device import router as device_router
from routers.shipments import router as shipments_router

__all__ = ["auth_router", "device_router", "shipments_router"]
