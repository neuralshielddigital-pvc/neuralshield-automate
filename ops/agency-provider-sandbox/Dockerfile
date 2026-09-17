FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /work
COPY backend/requirements.txt /work/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app /work/backend/app
COPY ops/agency-provider-sandbox/sandbox_app.py ops/agency-provider-sandbox/checkout.html ops/agency-provider-sandbox/member.html /work/ops/agency-provider-sandbox/
USER 65534:65534
