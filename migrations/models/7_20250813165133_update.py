from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "analysis_results" ADD "analysing_model" VARCHAR(15);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "analysis_results" DROP COLUMN "analysing_model";"""
