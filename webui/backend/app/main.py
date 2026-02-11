"""
Main FastAPI application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import auth, services, core, system, vhosts, dns, community
from app.services.vhost_indexer import VhostIndexer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    await init_db()

    # Initialize vhost indexer with background refresh
    # This will create the database, perform initial index if needed,
    # and start a background task to refresh every 2 hours
    await VhostIndexer.start_background_refresh(initial_rebuild=False)

    yield

    # Shutdown
    # Stop the background refresh task
    await VhostIndexer.stop_background_refresh()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Web-based management interface for Fauxnet network simulation environment",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Include routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(core.router)
app.include_router(system.router)
app.include_router(vhosts.router)
app.include_router(dns.router)
app.include_router(community.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
