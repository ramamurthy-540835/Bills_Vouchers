from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "development-only-change-me"
    database_url: str = "sqlite:///./finance.db"
    max_upload_mb: int = 15
    gcp_project_id: str = ""
    gcp_region: str = "asia-south1"
    gcs_bucket_name: str = ""
    bigquery_dataset: str = "finance_analytics"
    document_ai_location: str = "us"
    document_ai_processor_id: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings: return Settings()
