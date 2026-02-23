from fastapi import FastAPI
from app.api.v1.sms import router as sms_router
from app.api.v1.search import router as search_router
from app.config import settings
from app.core.providers.search import init_search_providers

app = FastAPI(title="SMS + Search Bridge API")

# Init search providers on startup
@app.on_event("startup")
async def startup():
    init_search_providers(
        api_key=settings.brave_api_key if hasattr(settings, "brave_api_key") else "",
        api_url=getattr(settings, "brave_api_url", "https://api.search.brave.com/res/v1/web/search"),
    )

app.include_router(sms_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"ok": True, "service": "sms-bridge"}
