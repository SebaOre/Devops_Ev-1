FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    USERS_SERVICE_URL=http://usuarios:8000

WORKDIR /app

COPY estadisticas/requirements.txt estadisticas/requirements.lock ./
RUN python -m pip install --only-binary :all: --require-hashes \
        -r requirements.lock -r requirements.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY estadisticas/app ./app

USER 10001:10001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)"]

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

ARG VCS_REF=local
ARG SOURCE_URL=https://github.com/SebaOre/Devops_Ev-1
LABEL org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.source=$SOURCE_URL
