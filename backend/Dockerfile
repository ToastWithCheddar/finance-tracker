# backend/Dockerfile — multi-stage. `prod` target = thin runtime image.
#
# Stages:
#   builder      : full toolchain, builds wheels into /install
#   prod         : runtime — slim image, non-root, no compilers, healthcheck
#   dev          : convenience target retaining build tools + uvicorn --reload
#
# Build:
#   docker build --target prod -t finance-tracker/backend:prod .
#
# Findings addressed: INFRA-DOCK-004 (multi-stage), BE-PR-005 (uvicorn args).

# =============================================================================
# Stage 1: builder — compile wheels with full toolchain
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install into a single prefix that we copy whole into the runtime stage.
COPY requirements-prod.txt requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements-prod.txt

# =============================================================================
# Stage 2: prod — minimal runtime
# =============================================================================
FROM python:3.11-slim AS prod

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    WEB_CONCURRENCY=4

# Runtime libs only — libpq5 for psycopg, curl for healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
        passwd \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 appuser \
    && useradd  --system --uid 1001 --gid appuser --home /home/appuser --create-home appuser

# Copy the prebuilt site-packages from the builder stage.
COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=appuser:appuser . /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Use tini as PID 1 for proper signal handling. WEB_CONCURRENCY drives uvicorn
# worker count; --workers is honored when >1 to avoid the dev single-worker path.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-4} --log-level ${LOG_LEVEL:-info} --proxy-headers --forwarded-allow-ips='*'"]

# =============================================================================
# Stage 3: dev — keeps reload + tools (used by repo-root docker-compose.yml)
# =============================================================================
FROM builder AS dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY . /app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
