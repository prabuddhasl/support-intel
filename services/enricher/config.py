import os


BOOTSTRAP = os.environ["BOOTSTRAP"]
TOPIC_IN = os.environ["TOPIC_IN"]
TOPIC_OUT = os.environ["TOPIC_OUT"]
TOPIC_DLQ = os.environ["TOPIC_DLQ"]
GROUP_ID = os.environ.get("GROUP_ID", "support-enricher")
DATABASE_URL = os.environ["DATABASE_URL"]
MODEL = os.environ.get("MODEL", "claude-sonnet-4-5-20250929")
