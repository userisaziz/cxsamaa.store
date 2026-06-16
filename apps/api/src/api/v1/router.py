from fastapi import APIRouter

from src.api.v1.analytics import router as analytics_router
from src.api.v1.auth import router as auth_router
from src.api.v1.brands import router as brands_router
from src.api.v1.conversations import router as conversations_router
from src.api.v1.hierarchy import router as hierarchy_router
from src.api.v1.recordings import router as recordings_router
from src.api.v1.salespeople import router as salespeople_router
from src.api.v1.search import router as search_router
from src.api.v1.stores import router as stores_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(brands_router)
api_v1_router.include_router(stores_router)
api_v1_router.include_router(salespeople_router)
api_v1_router.include_router(recordings_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(hierarchy_router)
