import os

import aioboto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from loguru import logger

from app.config import ConfigName, _load_settings

load_dotenv()
CONFIG_NAME = ConfigName(os.getenv("CONFIG_NAME", "development"))
settings = _load_settings(config_name=CONFIG_NAME)


class AsyncS3Manager:
    endpoint_url = settings.ENDPOINT_URL
    region_name = settings.REGION_NAME
    aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    bucket_name = settings.BUCKET_NAME
    bucket_folder = settings.APP

    def _get_session(self):
        return aioboto3.Session()

    def _build_path(self, chat_id: int, filename: str) -> str:
        return f"{self.bucket_folder}/{chat_id}/{filename}"

    def _get_client(self):
        session = self._get_session()
        return session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    async def upload_bytes(self, file_bytes: bytes, chat_id: int, filename: str):
        key = self._build_path(chat_id, filename)

        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                await s3.put_object(Bucket=self.bucket_name, Key=key, Body=file_bytes, ACL="private")
                logger.info(f"✅ Файл загружен: {key}")
                return key
            except ClientError as e:
                logger.error(f"Ошибка загрузки: {e}")
                raise

    async def generate_presigned_url(self, key, expiration=3600):
        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                return await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expiration,
                )
            except ClientError as e:
                logger.error(f"Ошибка при генерации ссылки: {e}")
                return None

    async def list_chat_files(self, chat_id: int) -> list[str]:
        prefix = f"{self.bucket_folder}/{chat_id}/"
        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                response = await s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                return [obj["Key"] for obj in response.get("Contents", [])]
            except ClientError as e:
                logger.error(f"Ошибка при получении списка файлов: {e}")
                return []
