"""S3-compatible object store settings (RustFS, MinIO, AWS): S3_*."""

from __future__ import annotations

from dataclasses import dataclass

from ._base import EnvSettings, Secret, setting


@dataclass(init=False, repr=False, kw_only=True)
class S3Settings(EnvSettings):
    s3_endpoint: str = setting("S3_ENDPOINT")
    s3_region: str = setting("S3_REGION", default="us-east-1")
    s3_bucket: str = setting("S3_BUCKET")
    s3_force_path_style: bool = setting("S3_FORCE_PATH_STYLE", default=True)
    # SECRETS: required, no default; NAME or NAME_FILE
    s3_access_key: Secret = setting("S3_ACCESS_KEY")
    s3_secret_key: Secret = setting("S3_SECRET_KEY")
