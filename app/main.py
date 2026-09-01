import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.session import init_db
from app.api import auth, setup, calendars, tasks, habits, biometrics, finance, integrations, agent, voice

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    await init_db()
    yield

app = FastAPI(
    title="Plexi AI Executive Assistant",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
api_prefix = settings.API_V1_STR
app.include_router(setup.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(calendars.router, prefix=api_prefix)
app.include_router(tasks.router, prefix=api_prefix)
app.include_router(habits.router, prefix=api_prefix)
app.include_router(biometrics.router, prefix=api_prefix)
app.include_router(finance.router, prefix=api_prefix)
app.include_router(integrations.router, prefix=api_prefix)
app.include_router(agent.router, prefix=api_prefix)
app.include_router(voice.router, prefix=api_prefix)

# Mount static web dashboard & setup wizard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Plexi AI is running. Access /docs for API or /static for Web UI."}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": "Plexi",
        "version": settings.VERSION,
        "database": "sqlite_async"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
