from abc import ABC, abstractmethod
import httpx
from typing import List, Dict, Any
from app.config import settings


class SearchClient(ABC):
    @abstractmethod
    async def search(self, query: str, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        ...


class BraveSearchProvider(SearchClient):
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url

    async def search(self, query: str, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if options is None:
            options = {}
        params = {
            "q": query,
            "count": options.get("limit", 5),
        }
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.api_url, params=params, headers=headers)
        results = []
        try:
            data = resp.json()
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title"),
                    "snippet": item.get("description"),
                    "url": item.get("url"),
                })
        except Exception:
            results = []
        return results


# Provider registry
from typing import Dict as DictType

search_providers: DictType[str, SearchClient] = {}


def get_search_provider(name: str) -> SearchClient:
    if name not in search_providers:
        raise ValueError(f"Unknown search provider: {name}")
    return search_providers[name]


def init_search_providers(api_key: str, api_url: str):
    search_providers["brave_search"] = BraveSearchProvider(api_key=api_key, api_url=api_url)
