# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.6.6 AS uv_bin

# --- Stage 1: build production virtual environment ---------------------------
FROM python:3.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv_bin /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Stage 2: optional test target (includes dev dependencies) ---------------
FROM builder AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src"
CMD ["pytest"]

# --- Stage 3: minimal non-root production runtime ----------------------------
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src" \
    DJANGO_SETTINGS_MODULE="config.settings"

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --home-dir /app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src /app/src
COPY --chown=app:app entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/src/staticfiles /app/data && \
    python src/manage.py collectstatic --noinput && \
    chown -R app:app /app/src/staticfiles /app/data

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/accounts/login/', timeout=2)" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--chdir", "/app/src", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
