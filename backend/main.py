import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.routes.facts import router as facts_router
from backend.routes.payments import router as payments_router
from backend.routes.admin import router as admin_router
from backend.routes.analytics import router as analytics_router
from data.init_db import init_database_and_seed


# Rate limiting setup
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed Facts on Startup
    try:
        await init_database_and_seed()
    except Exception as e:
        print(f"Database initialization warning: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="One rupee. One new thing. Minimal curious facts platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(facts_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(analytics_router)


# SEO & Root Endpoints
@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    robots_path = os.path.join("frontend", "robots.txt")
    if os.path.exists(robots_path):
        return FileResponse(robots_path, media_type="text/plain")
    return JSONResponse(status_code=404, content={"message": "Not found"})


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    sitemap_path = os.path.join("frontend", "sitemap.xml")
    if os.path.exists(sitemap_path):
        return FileResponse(sitemap_path, media_type="application/xml")
    return JSONResponse(status_code=404, content={"message": "Not found"})


@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    fav_path = os.path.join("frontend", "favicon.svg")
    if os.path.exists(fav_path):
        return FileResponse(fav_path, media_type="image/svg+xml")
    return JSONResponse(status_code=404, content={"message": "Not found"})


@app.get("/admin", include_in_schema=False)
async def admin_page():
    admin_path = os.path.join("frontend", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return JSONResponse(status_code=404, content={"message": "Admin page not found"})


# Health Check
@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "payment_mode": settings.PAYMENT_MODE,
        "env": settings.APP_ENV
    }


# Mount Frontend Static Files at the root
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if not os.path.exists(frontend_dir):
    frontend_dir = "frontend"

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
