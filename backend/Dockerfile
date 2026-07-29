# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
WORKDIR /app

# Install system dependencies for psycopg binary
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./

# Install runtime dependencies only (no dev extras)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
