"""FastAPI application entry point.

Responsible only for creating the app, wiring middleware, and registering
routers. No business logic belongs in this file.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import drones, health, pipeline, stats
from app.config import settings

app = FastAPI(title="Drone Activity Map Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(pipeline.router)
app.include_router(drones.router)
app.include_router(stats.router)
