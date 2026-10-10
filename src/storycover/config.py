from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Synced into the pod by the Vault Secrets Operator; never baked into the image.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-image"

    # GCS bucket for generated covers (created in the infra repo).
    gcs_bucket: str = ""
    # Identity used to sign URLs; defaults to the Workload Identity SA at runtime.
    signer_service_account: str = ""
    signed_url_ttl_seconds: int = 900

    # Reject uploads larger than this before touching Gemini.
    max_upload_bytes: int = 8 * 1024 * 1024


settings = Settings()
