"""S3-compatible object store adapter (RustFS, MinIO, AWS) on boto3.

boto3 is synchronous: every call runs in a worker thread so the event loop is
never blocked. Credentials and endpoint come from `Settings` (S3_* variables).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from ..settings import S3Settings


class ObjectNotFoundError(LookupError):
    """The object (or bucket) does not exist."""


class ObjectStore:
    def __init__(self, settings: S3Settings) -> None:
        self.bucket = settings.s3_bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key.get_secret_value(),
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
            config=Config(
                s3={
                    "addressing_style": (
                        "path" if settings.s3_force_path_style else "virtual"
                    )
                },
                # S3-compatible stores do not all accept the SDK's default
                # trailing checksums: send them only when required.
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=30,
            ),
        )

    async def _run(self, fn: Callable[..., Any], /, **kwargs: Any) -> Any:
        return await asyncio.to_thread(fn, **kwargs)

    async def ping(self) -> None:
        """The bucket exists and the credentials may use it."""
        await self._run(self._s3.head_bucket, Bucket=self.bucket)

    async def ensure_bucket(self) -> None:
        """Create the bucket when missing (tests, local setup only)."""
        try:
            await self.ping()
        except ClientError:
            await self._run(self._s3.create_bucket, Bucket=self.bucket)

    async def put(
        self, key: str, body: bytes, content_type: str = "application/json"
    ) -> None:
        await self._run(
            self._s3.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        try:
            out = await self._run(
                self._s3.get_object, Bucket=self.bucket, Key=key
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(key) from None
            raise
        return await asyncio.to_thread(out["Body"].read)

    async def delete(self, key: str) -> None:
        await self._run(self._s3.delete_object, Bucket=self.bucket, Key=key)

    async def list(self, prefix: str, limit: int = 1000) -> list[str]:
        """At most `limit` keys under `prefix` (bounded)."""
        out = await self._run(
            self._s3.list_objects_v2,
            Bucket=self.bucket,
            Prefix=prefix,
            MaxKeys=limit,
        )
        return [obj["Key"] for obj in out.get("Contents", [])]
