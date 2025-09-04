from __future__ import annotations

import os
import time

import boto3
from botocore.client import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "web-raw")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def store_raw(url: str, html: str, content_hash: str) -> str:
    t = int(time.time())
    key = f"web_raw/{t}/{content_hash}.html"
    _client().put_object(
        Bucket=MINIO_BUCKET, Key=key, Body=html.encode("utf-8"), ContentType="text/html"
    )
    return f"s3://{MINIO_BUCKET}/{key}"
