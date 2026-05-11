from __future__ import annotations

import os
from pathlib import Path
import time

from sqlalchemy import create_engine

from app.core.config import settings
from app.db import session as db_session_module
from app.services.jobs import background_jobs as jobs_module
from app.services.jobs.background_jobs import process_import_job


def _sa_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class CrashImportExecutor:
    def execute(self, **_kwargs):
        signal_file = Path(os.environ["CRASH_SIGNAL_FILE"])
        signal_file.write_text("ready", encoding="ascii")
        while True:
            time.sleep(0.2)


def main() -> int:
    database_url = os.environ["TEST_DATABASE_URL"]
    job_id = os.environ["CRASH_JOB_ID"]
    settings.database_url = database_url
    engine = create_engine(_sa_url(database_url), pool_pre_ping=True)
    db_session_module._engine = engine
    jobs_module.ImportExecutor = CrashImportExecutor
    try:
        process_import_job(job_id, engine)
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
