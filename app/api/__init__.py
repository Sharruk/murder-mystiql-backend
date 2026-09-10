"""API router module."""
from fastapi import APIRouter
from app.api.session import router as session_router
from app.api.level import router as level_router
from app.api.query import router as query_router
from app.api.answer import router as answer_router
from app.api.hint import router as hint_router
from app.api.leaderboard import router as leaderboard_router
from app.api.proctor import router as proctor_router

api_router = APIRouter(prefix="/api")

api_router.include_router(session_router, prefix="/session", tags=["Session"])
api_router.include_router(level_router, prefix="/level", tags=["Level"])
api_router.include_router(query_router, prefix="/query", tags=["Query"])
api_router.include_router(answer_router, prefix="/answer", tags=["Answer"])
api_router.include_router(hint_router, prefix="/hint", tags=["Hint"])
api_router.include_router(leaderboard_router, prefix="/leaderboard", tags=["Leaderboard"])
api_router.include_router(proctor_router, prefix="/proctor", tags=["Proctor"])
