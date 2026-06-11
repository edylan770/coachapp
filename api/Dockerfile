FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/api

COPY . .
RUN pip install . && chmod +x docker-entrypoint.sh

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
