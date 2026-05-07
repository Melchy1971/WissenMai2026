from __future__ import annotations

import os
from pathlib import Path
import time

import uvicorn

from app.main import app
from app.services.jobs import background_jobs as jobs_module


def _crash_temp_upload_file(*, filename: str, source_bytes: bytes) -> str:
    signal_file = Path(os.environ["CRASH_SIGNAL_FILE"])
    temp_file = Path(os.environ["CRASH_TEMP_FILE"])
    temp_file.write_bytes(source_bytes)
    signal_file.write_text("ready", encoding="ascii")
    while True:
        time.sleep(0.2)


def main() -> int:
    jobs_module.BackgroundJobService.create_temp_upload_file = staticmethod(_crash_temp_upload_file)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["CRASH_SERVER_PORT"]), log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())