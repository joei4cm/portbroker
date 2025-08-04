from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.router import api_router
from app.core.auth import get_current_portal_user
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="PortBroker",
    description="API service that translates Anthropic API to OpenAI compatible format",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files and templates
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(frontend_dir / "templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "PortBroker API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Note: Portal routes are handled by the providers router under /portal prefix
# The login and dashboard routes are now in providers.py
