FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/api

COPY . .
RUN pip install . && chmod +x docker-entrypoint.sh

# Pre-create the storage mount point owned by the app user (named volumes
# inherit ownership from the image path on first use).
RUN useradd --create-home appuser && \
    mkdir -p /srv/api/storage-data && \
    chown appuser:appuser /srv/api/storage-data
USER appuser

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
