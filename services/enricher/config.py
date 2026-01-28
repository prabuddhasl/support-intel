from services.enricher.settings import get_settings

_settings = get_settings()

BOOTSTRAP = _settings.bootstrap
TOPIC_IN = _settings.topic_in
TOPIC_OUT = _settings.topic_out
TOPIC_DLQ = _settings.topic_dlq
GROUP_ID = _settings.group_id
DATABASE_URL = _settings.database_url
MODEL = _settings.model
