from __future__ import annotations

from fastapi import FastAPI

from .routers import forecasts, health


api = FastAPI(
    title="Truong Ton Farm API",
    version="0.1.0",
    description="Read-only API extracted from the Streamlit input app.",
)

api.include_router(health.router)
api.include_router(forecasts.router)
