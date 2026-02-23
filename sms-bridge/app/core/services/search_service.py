from app.core.providers.search import get_search_provider
from app.models.schemas import SearchRequest, SearchResponse


async def search_web(req: SearchRequest) -> SearchResponse:
    provider_name = req.provider or "brave_search"
    client = get_search_provider(provider_name)
    options = {"limit": req.limit or 5}
    results = await client.search(req.query, options=options)
    return SearchResponse(success=True, results=results, detail={"provider": provider_name})
