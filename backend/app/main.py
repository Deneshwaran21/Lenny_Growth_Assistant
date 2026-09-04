from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routers import artifacts, chat, sessions, system

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("lenny.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (env=%s, provider=%s)", settings.APP_NAME, settings.ENVIRONMENT, settings.LLM_PROVIDER
    )
    try:
        await init_db()
        logger.info("Database tables ensured.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Database initialization failed at startup: %s. API will report degraded health.", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Grounded conversational assistant over Lenny's Podcast transcripts.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs for details."},
    )


app.include_router(system.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(artifacts.router)


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "status": "running", "docs": "/docs"}
