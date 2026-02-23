from app.core.providers.sms import get_provider
from app.models.schemas import SendRequest, SendResponse


async def send_sms(req: SendRequest) -> SendResponse:
    provider_name = req.provider or "textlink_sms"
    client = get_provider(provider_name)
    result = await client.send(req.to, req.message)
    return SendResponse(success=bool(result.get("ok", False)), detail=result)
