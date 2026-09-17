FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /work
COPY backend/requirements.txt backend/requirements-dev.txt /work/backend/
RUN python -m pip install --no-cache-dir -r backend/requirements-dev.txt
COPY backend/app /work/backend/app
COPY backend/tests /work/backend/tests
COPY backend/alembic /work/backend/alembic
COPY backend/alembic.ini backend/pytest.ini /work/backend/
COPY scripts/run_agency_postgres_validation.py /work/scripts/run_agency_postgres_validation.py
USER 65534:65534
CMD ["python", "scripts/run_agency_postgres_validation.py"]
