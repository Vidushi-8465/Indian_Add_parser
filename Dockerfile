# Indian Address Search — API image (Phase 9)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application source.
COPY . .

EXPOSE 8000

# The API reads Elasticsearch host from configs/elasticsearch.yaml (override via
# ES_HOST / env or a mounted config). Runs the full search pipeline.
CMD ["python", "scripts/run_api.py"]
