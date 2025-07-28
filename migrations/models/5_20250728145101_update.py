from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chat_schedules" ADD "description" TEXT;
        ALTER TABLE "chat_schedules" ADD "name" VARCHAR(255);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chat_schedules" DROP COLUMN "description";
        ALTER TABLE "chat_schedules" DROP COLUMN "name";"""
