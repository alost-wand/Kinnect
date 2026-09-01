"""backend/main.py — KINNECT FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database import get_pool, close_pool
from backend.routers import auth, timeline, wearable, emergency, vault, privacy


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()          # warm-up DB pool
    yield
    await close_pool()        # clean shutdown


app = FastAPI(
    title="KINNECT API",
    description="Family connectivity platform — modular FastAPI backend.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────
app.include_router(auth.router)
app.include_router(timeline.router)
app.include_router(wearable.router)
app.include_router(emergency.router)
app.include_router(vault.router)
app.include_router(privacy.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "KINNECT backend online ✅"}
