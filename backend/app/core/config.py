from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "local"
    database_url: str | None = None
    default_workspace_id: str = "00000000-0000-0000-0000-000000000001"
    default_user_id: str = "00000000-0000-0000-0000-000000000001"
    max_upload_size_bytes: int = 50 * 1024 * 1024
    admin_api_token: str = "local-admin-token"
    import_jobs_temp_dir: str | None = None
    original_file_store_dir: str | None = None
    backup_restore_root_dir: str | None = None
    background_job_lock_timeout_seconds: int = 300
    background_job_heartbeat_interval_seconds: int = 30
    background_job_max_attempts: int = 3
    background_job_retry_backoff_seconds: int = 30


settings = Settings()
