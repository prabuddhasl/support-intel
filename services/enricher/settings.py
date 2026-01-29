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
    embedding_model: str = Field("BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    rerank_model: str = Field("BAAI/bge-reranker-base", alias="RERANK_MODEL")
    kb_top_k: int = Field(5, alias="KB_TOP_K")
    kb_candidates: int = Field(20, alias="KB_CANDIDATES")
    rerank_enabled: bool = Field(True, alias="RERANK_ENABLED")
    hybrid_search_enabled: bool = Field(True, alias="HYBRID_SEARCH_ENABLED")
    hybrid_keyword_max: int = Field(20, alias="HYBRID_KEYWORD_MAX")


_settings: EnricherSettings | None = None


def get_settings() -> EnricherSettings:
    global _settings
    if _settings is None:
        _settings = EnricherSettings()  # type: ignore[call-arg]
    return _settings
