"""PostgreSQL backup → gzip → S3 upload with retention cleanup.

Runs as dedicated Docker Compose service. Dormant when S3_BUCKET/S3_ACCESS_KEY absent.
Schedule: daily at 02:00 Asia/Yekaterinburg (UTC+5).
Retention: 14 days daily, up to 6 months keep 1st-of-month, older deleted.
"""
import gzip
import io
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import boto3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Yekaterinburg")
_BACKUP_HOUR = 2
_S3_PREFIX = os.environ.get("S3_PREFIX", "backups")


def _is_configured() -> bool:
    return bool(os.environ.get("S3_BUCKET") and os.environ.get("S3_ACCESS_KEY"))


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name=os.environ.get("S3_REGION", "ru-1"),
    )


def _seconds_until_next_run() -> float:
    now = datetime.now(_TZ)
    next_run = now.replace(hour=_BACKUP_HOUR, minute=0, second=0, microsecond=0)
    if now >= next_run:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


def _dump_database() -> bytes:
    env = os.environ.copy()
    env["PGPASSWORD"] = os.environ["DB_PASSWORD"]
    result = subprocess.run(
        [
            "pg_dump",
            "-h", os.environ.get("DB_HOST", "db"),
            "-p", os.environ.get("DB_PORT", "5432"),
            "-U", os.environ["DB_USER"],
            "-d", os.environ["DB_NAME"],
            "--no-password",
        ],
        capture_output=True,
        env=env,
        check=True,
    )
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(result.stdout)
    return buf.getvalue()


def _upload(client, data: bytes, filename: str) -> None:
    bucket = os.environ["S3_BUCKET"]
    key = f"{_S3_PREFIX.rstrip('/')}/{filename}"
    client.put_object(Bucket=bucket, Key=key, Body=data)
    logger.info("Uploaded %s (%d bytes) → s3://%s/%s", filename, len(data), bucket, key)


def _apply_retention(client) -> None:
    bucket = os.environ["S3_BUCKET"]
    prefix = _S3_PREFIX.rstrip("/") + "/"
    today = datetime.now(_TZ).date()
    cutoff_daily = today - timedelta(days=14)
    cutoff_monthly = today - timedelta(days=183)

    paginator = client.get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.rsplit("/", 1)[-1]
            if not (filename.startswith("backup_") and filename.endswith(".sql.gz")):
                continue
            try:
                date_str = filename[7:17]  # backup_YYYY-MM-DD.sql.gz → YYYY-MM-DD
                backup_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if backup_date > cutoff_daily:
                continue  # last 14 days — keep
            if backup_date > cutoff_monthly and backup_date.day == 1:
                continue  # monthly snapshot — keep
            # everything else: delete
            client.delete_object(Bucket=bucket, Key=key)
            logger.info("Retention: deleted %s", key)
            deleted += 1

    if deleted:
        logger.info("Retention: removed %d object(s)", deleted)


def _run_backup() -> None:
    logger.info("Backup started")
    try:
        data = _dump_database()
        filename = f"backup_{datetime.now(_TZ).strftime('%Y-%m-%d')}.sql.gz"
        client = _s3_client()
        _upload(client, data, filename)
        _apply_retention(client)
        logger.info("Backup finished: %s", filename)
    except subprocess.CalledProcessError as exc:
        logger.error("pg_dump failed (exit %d): %s", exc.returncode, exc.stderr.decode())
    except Exception:
        logger.exception("Backup failed")


def main() -> None:
    if not _is_configured():
        logger.info("Backup not configured (S3_BUCKET/S3_ACCESS_KEY missing) — dormant")
        while True:
            time.sleep(3600)

    logger.info("Backup service ready. TZ=%s, runs at %02d:00 daily", _TZ.key, _BACKUP_HOUR)
    while True:
        wait = _seconds_until_next_run()
        next_dt = datetime.now(_TZ) + timedelta(seconds=wait)
        logger.info("Next backup: %s (in %.0fs)", next_dt.strftime("%Y-%m-%d %H:%M %Z"), wait)
        time.sleep(wait)
        _run_backup()


if __name__ == "__main__":
    main()
