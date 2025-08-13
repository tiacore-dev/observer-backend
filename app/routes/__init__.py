from fastapi import FastAPI
from tiacore_lib.routes.auth_route import auth_router
from tiacore_lib.routes.company_route import company_router
from tiacore_lib.routes.invite_route import invite_router
from tiacore_lib.routes.register_route import register_router
from tiacore_lib.routes.reset_password_route import reset_router
from tiacore_lib.routes.role_route import role_router
from tiacore_lib.routes.user_route import user_router

from .agreement_route import agreement_router
from .analysis_route import analysis_router
from .bot_route import bot_router
from .get_route import get_router
from .monitoring_route import monitoring_router
from .prompt_route import prompt_router
from .schedule_route import schedule_router
from .webhook_route import webhook_router


def register_routes(app: FastAPI):
    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(invite_router, prefix="/api", tags=["Invite"])
    app.include_router(register_router, prefix="/api", tags=["Register"])
    app.include_router(agreement_router, prefix="/api", tags=["UserAgreement"])
    app.include_router(reset_router, prefix="/api", tags=["ResetPassword"])
    app.include_router(user_router, prefix="/api/users", tags=["Users"])
    app.include_router(company_router, prefix="/api/companies", tags=["Companies"])
    app.include_router(role_router, prefix="/api/roles", tags=["Roles"])
    app.include_router(bot_router, prefix="/api/bots", tags=["Bots"])
    app.include_router(prompt_router, prefix="/api/prompts", tags=["Prompts"])
    app.include_router(webhook_router, prefix="/api/webhook", tags=["Webhooks"])
    app.include_router(schedule_router, prefix="/api/schedules", tags=["Schedules"])
    app.include_router(analysis_router, prefix="/api/analysis", tags=["Analysis"])

    app.include_router(monitoring_router, tags=["Monitoring"])
    app.include_router(get_router, prefix="/api", tags=["Get"])
