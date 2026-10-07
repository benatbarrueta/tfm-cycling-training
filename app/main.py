from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import activities, auth, health, profile, season_plans
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Veloform API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(activities.router, prefix="/api")
app.include_router(season_plans.router, prefix="/api")
