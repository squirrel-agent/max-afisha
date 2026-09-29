from fastapi import APIRouter

from app.api.routes import admin, cities, dev, events, feed, max_integration, ml, recommendations, search, sources, users

api_router = APIRouter(prefix="/api")

api_router.include_router(events.router)
api_router.include_router(cities.router)
api_router.include_router(dev.router)
api_router.include_router(sources.router)
api_router.include_router(ml.router)
api_router.include_router(search.router)
api_router.include_router(feed.router)
api_router.include_router(max_integration.router)

api_router.include_router(admin.router)
api_router.include_router(users.router)
api_router.include_router(recommendations.router)
