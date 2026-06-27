# ml-worker/Dockerfile — multi-stage. Two prod targets:
#   prod              : standard runtime (models can be baked or volume-mounted)
#   prod-no-models    : weights fetched at startup via scripts/fetch_models.sh
#
# Findings addressed: INFRA-DOCK-004 (multi-stage), INFRA-DOCK-005 (no weights
# in image), ML-PR-005 (fetch script).

# =============================================================================
# Stage 1: builder — compilers + git for any pip-VCS deps
# =============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

# =============================================================================
# Stage 2: runtime-base — shared runtime layer (no compilers, no git)
# =============================================================================
FROM python:3.11-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MODELS_DIR=/models

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
        tini \
        passwd \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 worker \
    && useradd  --system --uid 1001 --gid worker --home /home/worker --create-home worker

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=worker:worker . /app
RUN mkdir -p /models /app/data /app/ab_test_results \
    && chown -R worker:worker /models /app/data /app/ab_test_results

# =============================================================================
# Stage 3: prod — standard target. Models may already be present in the
# /models volume or baked in via a downstream COPY.
# =============================================================================
FROM runtime-base AS prod

USER worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD celery -A worker inspect ping -d "celery@$(hostname)" >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["celery", "-A", "worker", "worker", \
     "--loglevel=info", "--concurrency=2", "--max-tasks-per-child=1000", \
     "--without-mingle", "--without-gossip"]

# =============================================================================
# Stage 4: prod-no-models — weights fetched at runtime (preferred for prod).
# scripts/fetch_models.sh is idempotent: if /models is non-empty it exits 0.
# =============================================================================
FROM runtime-base AS prod-no-models

# Ensure the fetch script is executable.
RUN chmod +x /app/scripts/fetch_models.sh || true

USER worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD test -f /models/.ready && \
        celery -A worker inspect ping -d "celery@$(hostname)" >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/fetch_models.sh"]
CMD ["celery", "-A", "worker", "worker", \
     "--loglevel=info", "--concurrency=2", "--max-tasks-per-child=1000", \
     "--without-mingle", "--without-gossip"]
