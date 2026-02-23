from fastapi import APIRouter
from app.models.schemas import SendRequest, SendResponse
from app.core.services.sms_service import send_sms

router = APIRouter()


@router.post("/send", response_model=SendResponse)
async def send(req: SendRequest):
    return await send_sms(req)
