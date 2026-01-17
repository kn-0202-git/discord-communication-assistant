FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-install-project

COPY config.yaml /app/config.yaml
COPY src /app/src

RUN mkdir -p /app/data/files

CMD ["python", "-m", "src.main"]
