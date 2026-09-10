from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "development-only-change-me"
    max_upload_mb: int = 15
    bootstrap_admin_email: str = "stephenraj040899@gmail.com"
    bootstrap_admin_password: str = ""
    session_max_age: int = 28800
    session_idle_timeout: int = 1800
    max_query_bytes: int = 100000000
    query_timeout_seconds: int = 60
    gcp_project_id: str = ""
    gcp_region: str = "global"
    gcs_bucket_name: str = ""
    bigquery_dataset: str = "finance_analytics"
    gemini_model: str = "gemini-3.8-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    gemini_api_key: str = ""
    gemini_enabled: bool = True
    cloud_tasks_queue: str = ""
    cloud_tasks_service_url: str = ""
    cloud_tasks_service_account: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    return Settings()
