from services.api.settings import get_settings

_settings = get_settings()

DATABASE_URL = _settings.database_url
BOOTSTRAP = _settings.bootstrap
TOPIC_IN = _settings.topic_in
