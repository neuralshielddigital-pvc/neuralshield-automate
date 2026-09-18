FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /relay
RUN python -m pip install --no-cache-dir fastapi==0.115.6 starlette==0.41.3 uvicorn==0.34.0
COPY webhook_relay.py /relay/webhook_relay.py
USER 65534:65534
