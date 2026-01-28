from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    bootstrap: str = Field("kafka:9092", alias="BOOTSTRAP")
    topic_in: str = Field("support.tickets.v1", alias="TOPIC_IN")


_settings: ApiSettings | None = None


def get_settings() -> ApiSettings:
    global _settings
    if _settings is None:
        _settings = ApiSettings()  # type: ignore[call-arg]
    return _settings
