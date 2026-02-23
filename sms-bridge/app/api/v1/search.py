from fastapi import APIRouter
from app.models.schemas import SearchRequest, SearchResponse
from app.core.services.search_service import search_web

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    return await search_web(req)
