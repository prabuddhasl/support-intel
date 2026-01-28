import os


DATABASE_URL = os.environ["DATABASE_URL"]
BOOTSTRAP = os.environ.get("BOOTSTRAP", "kafka:9092")
TOPIC_IN = os.environ.get("TOPIC_IN", "support.tickets.v1")
