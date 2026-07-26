"""
Main FastAPI Server & Microservice Assembly for JARVIS OS.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jarvis.config.settings import settings
from jarvis.api.routes.intent import router as intent_router
from jarvis.api.routes.approval import router as approval_router
from jarvis.api.routes.agents import router as agents_router
from jarvis.api.routes.logs import router as logs_router
from jarvis.api.websocket import router as ws_router
from jarvis.utils.logger import get_logger

logger = get_logger("APIServer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for FastAPI startup and shutdown."""
    logger.info("JARVIS OS FastAPI microservice starting up...")
    yield
    logger.info("JARVIS OS FastAPI microservice shutting down...")


app = FastAPI(
    title="JARVIS OS - Enterprise AI Desktop Operating Layer",
    description="Local-first microservice API controlling desktop automation, multi-agent workflows, memory, and security.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(intent_router)
app.include_router(approval_router)
app.include_router(agents_router)
app.include_router(logs_router)
app.include_router(ws_router)


@app.get("/health", tags=["Health Check"])
async def health_check():
    """System health check endpoint."""
    return {"status": "online", "app": settings.APP_NAME, "version": "1.0.0"}
