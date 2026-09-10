"""
MurderMystiQL Backend Application.
FastAPI Application Entrypoint.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.db.connection import close_db, init_db, AsyncSessionLocal
from app.services.leaderboard_service import fetch_leaderboard
from app.websocket.leaderboard import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database connection pools
    print(f"[{settings.APP_NAME}] Starting up. Initializing database pools...")
    await init_db()
    yield
    # Shutdown: close pools
    print(f"[{settings.APP_NAME}] Shutting down. Closing database pools...")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="Offline LAN backend for MurderMystiQL SQL Murder Mystery Competition.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware (Crucial for offline LAN access from multiple participant machines)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router (/api/...)
app.include_router(api_router)


# Health Check
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# Live Leaderboard WebSocket Endpoint
@app.websocket("/ws/leaderboard")
async def websocket_leaderboard_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live leaderboard streaming.
    Immediately pushes current standings upon connection.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial standings if DB is available
        if AsyncSessionLocal is not None:
            async with AsyncSessionLocal() as db:
                lb = await fetch_leaderboard(db)
                await websocket.send_json({
                    "event": "LEADERBOARD_SNAPSHOT",
                    "data": lb.model_dump(mode="json"),
                })

        # Keep connection open for push notifications
        while True:
            # Client can send ping / heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# Static File Serving for Offline Built React Frontend
# If a built dist directory exists, serve it seamlessly
dist_path = Path(settings.FRONTEND_DIST_DIR) if settings.FRONTEND_DIST_DIR else None
if not dist_path or not dist_path.exists():
    # Fallback to local static directory
    dist_path = Path(__file__).parent.parent / "static"

if dist_path.exists():
    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API, WS, or docs
        if full_path.startswith(("api/", "ws/", "docs", "redoc", "openapi.json", "health")):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        file_candidate = dist_path / full_path
        if file_candidate.is_file():
            return FileResponse(str(file_candidate))

        index_file = dist_path / "index.html"
        if index_file.is_file():
            return FileResponse(str(index_file))

        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend assets not found."},
        )
