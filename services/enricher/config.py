from services.enricher.settings import get_settings

_settings = get_settings()

BOOTSTRAP = _settings.bootstrap
TOPIC_IN = _settings.topic_in
TOPIC_OUT = _settings.topic_out
TOPIC_DLQ = _settings.topic_dlq
GROUP_ID = _settings.group_id
DATABASE_URL = _settings.database_url
MODEL = _settings.model
EMBEDDING_MODEL = _settings.embedding_model
RERANK_MODEL = _settings.rerank_model
KB_TOP_K = _settings.kb_top_k
KB_CANDIDATES = _settings.kb_candidates
RERANK_ENABLED = _settings.rerank_enabled
HYBRID_SEARCH_ENABLED = _settings.hybrid_search_enabled
HYBRID_KEYWORD_MAX = _settings.hybrid_keyword_max
