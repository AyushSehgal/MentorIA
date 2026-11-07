"""NOVA FastAPI app. Run: uvicorn app.main:app --reload --port 8000 (from backend/)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, memory, sources
from .services.seed import ensure_seeded

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_seeded()
    yield


app = FastAPI(title="NOVA", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(sources.router)
app.include_router(memory.router)
app.include_router(chat.router)
