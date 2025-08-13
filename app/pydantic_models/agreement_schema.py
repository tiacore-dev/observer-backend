from uuid import UUID

from pydantic import BaseModel


class AgreementSchema(BaseModel):
    user_id: UUID

    class Config:
        from_attributes = True
