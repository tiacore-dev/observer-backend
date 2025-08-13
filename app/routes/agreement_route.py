from fastapi import APIRouter, Request, status

from app.database.models import UserAgreement
from app.pydantic_models.agreement_schema import AgreementSchema

agreement_router = APIRouter()


def get_client_ip(request: Request) -> str | None:
    # 1) Cloudflare
    ip = request.headers.get("CF-Connecting-IP")
    if ip:
        return ip.strip()

    # 2) Стандартные прокси-заголовки
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()  # первый = клиент

    xri = request.headers.get("X-Real-IP")
    if xri:
        return xri.strip()

    # 3) Фоллбэк — реальный TCP-пир (может быть None)
    return request.client.host if request.client else None


@agreement_router.post(  # лучше POST, не GET с Body
    "/agreement",
    summary="Логирование согласия пользователя на обработку персональных данных",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def log_agreement(request: Request, data: AgreementSchema):
    user_ip = get_client_ip(request) or "unknown"
    await UserAgreement.create(user_id=data.user_id, user_ip=user_ip)
