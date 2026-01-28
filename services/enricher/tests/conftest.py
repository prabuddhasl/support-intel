import os
import sys

# Ensure local module resolution for service modules.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Must set env vars at module scope — app.py reads os.environ["BOOTSTRAP"] etc.
# at import time, before any fixtures run.
os.environ.setdefault("BOOTSTRAP", "localhost:9092")
os.environ.setdefault("TOPIC_IN", "test.tickets")
os.environ.setdefault("TOPIC_OUT", "test.enriched")
os.environ.setdefault("TOPIC_DLQ", "test.dlq")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
