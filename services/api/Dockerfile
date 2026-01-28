FROM python:3.11-slim

WORKDIR /app

COPY services/api/requirements.txt ./services/api/requirements.txt
RUN pip install --no-cache-dir -r services/api/requirements.txt

COPY services ./services
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "services.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
