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


# Provide minimal stubs if optional document parsers aren't installed in the test env.
try:
    import pypdf  # noqa: F401
except Exception:
    class _StubPdfReader:
        def __init__(self, *args, **kwargs):
            self.pages = []

    sys.modules["pypdf"] = types.SimpleNamespace(PdfReader=_StubPdfReader)

try:
    import docx  # noqa: F401
except Exception:
    class _StubDocument:
        def __init__(self, *args, **kwargs):
            self.paragraphs = []

    sys.modules["docx"] = types.SimpleNamespace(Document=_StubDocument)


# Stub python-multipart for FastAPI UploadFile support in tests.
try:
    import python_multipart  # noqa: F401
except Exception:
    def _parse_options_header(value):
        return value, {}

    python_multipart_module = types.SimpleNamespace(__version__="0.0.13", __fake__=True)
    multipart_module = types.SimpleNamespace(parse_options_header=_parse_options_header)
    sys.modules["python_multipart"] = python_multipart_module
    sys.modules["multipart"] = types.SimpleNamespace(multipart=multipart_module)
    sys.modules["multipart.multipart"] = multipart_module
