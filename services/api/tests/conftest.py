import os
import sys
import types


# Ensure env vars exist before importing app.py (module-level reads).
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("BOOTSTRAP", "localhost:9092")
os.environ.setdefault("TOPIC_IN", "test.tickets")


# Provide a minimal stub if confluent_kafka isn't installed in the test env.
try:
    import confluent_kafka  # noqa: F401
except Exception:
    class _StubProducer:
        def __init__(self, *args, **kwargs):
            pass

        def produce(self, *args, **kwargs):
            pass

        def flush(self, *args, **kwargs):
            pass

    sys.modules["confluent_kafka"] = types.SimpleNamespace(Producer=_StubProducer)
