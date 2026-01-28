FROM python:3.11-slim

WORKDIR /app
COPY services/enricher/requirements.txt ./services/enricher/requirements.txt
RUN pip install --no-cache-dir -r services/enricher/requirements.txt

COPY services ./services
ENV PYTHONPATH=/app
CMD ["python", "-m", "services.enricher.app"]
