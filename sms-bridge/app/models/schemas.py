from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class SendRequest(BaseModel):
    to: str
    message: str
    provider: Optional[str] = None


class SendResponse(BaseModel):
    success: bool
    detail: Dict[str, Any]


class SearchRequest(BaseModel):
    query: str
    site: Optional[str] = None
    limit: Optional[int] = 5
    provider: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]
    detail: Optional[Dict[str, Any]] = None
