from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnricherSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bootstrap: str = Field(..., alias="BOOTSTRAP")
    topic_in: str = Field(..., alias="ENRICHER_TOPIC_IN")
    topic_out: str = Field(..., alias="TOPIC_OUT")
    topic_dlq: str = Field(..., alias="TOPIC_DLQ")
    group_id: str = Field("support-enricher", alias="GROUP_ID")
    database_url: str = Field(..., alias="DATABASE_URL")
    model: str = Field("claude-sonnet-4-5-20250929", alias="MODEL")


_settings: EnricherSettings | None = None


def get_settings() -> EnricherSettings:
    global _settings
    if _settings is None:
        _settings = EnricherSettings()  # type: ignore[call-arg]
    return _settings
