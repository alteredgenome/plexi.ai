from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.db.session import init_db
from app.api.auth import router as auth_router
from app.api.calendars import router as calendars_router
from app.api.tasks import router as tasks_router
from app.api.habits import router as habits_router
from app.api.biometrics import router as biometrics_router
from app.api.finance import router as finance_router
from app.api.integrations import router as integrations_router
from app.api.voice import router as voice_router
from app.api.agent import router as agent_router
from app.api.setup import router as setup_router
from app.api.admin import router as admin_router
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and WAL mode on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Open-Source Self-Hosted AI Executive Assistant & Daily Planner",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
api_v1_prefix = "/api/v1"
app.include_router(setup_router, prefix=api_v1_prefix)
app.include_router(admin_router, prefix=api_v1_prefix)
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(calendars_router, prefix=api_v1_prefix)
app.include_router(tasks_router, prefix=api_v1_prefix)
app.include_router(habits_router, prefix=api_v1_prefix)
app.include_router(biometrics_router, prefix=api_v1_prefix)
app.include_router(finance_router, prefix=api_v1_prefix)
app.include_router(integrations_router, prefix=api_v1_prefix)
app.include_router(voice_router, prefix=api_v1_prefix)
app.include_router(agent_router, prefix=api_v1_prefix)

# Mount Static UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "sqlite_async" if "sqlite" in settings.DATABASE_URL else "postgresql"
    }

@app.get("/", include_in_schema=False)
async def serve_root():
    from fastapi.responses import FileResponse
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
