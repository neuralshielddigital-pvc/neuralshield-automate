# NeuralShieldDigital Backend

Production-ready FastAPI foundation for the NeuralShieldDigital SaaS platform.

This scaffold includes:

- FastAPI app factory
- PostgreSQL configuration with SQLAlchemy 2.0
- Alembic migration setup
- Pydantic v2 settings
- JWT and bcrypt-ready security helpers
- Stripe-ready environment configuration
- Celery app configured for Redis
- Request ID middleware
- Security headers middleware
- CORS from environment
- Docker Compose for backend, PostgreSQL, and Redis

## Production notes

Production configuration is environment-only. Start from:

```bash
cp .env.production.example .env
```

Required production values:

- `DATABASE_URL`
- `SECRET_KEY`
- `BACKEND_CORS_ORIGINS`
- `TRUSTED_HOSTS`
- Stripe and SMTP secrets when those modules are enabled

Production hardening included:

- JSON logging via `LOG_FORMAT=json`
- secure CORS allowlist
- trusted host middleware
- configurable login and public lead rate limits
- request timeout middleware
- global exception handler with request IDs
- health check with database connectivity

Run migrations:

```bash
alembic upgrade head
```

Create an admin:

```bash
python scripts/create_admin.py --email admin@example.com --password 'StrongPassword!123' --super-admin
```

Run with systemd using:

```text
neuralshielddigital-backend.service
```

Use `nginx.conf.example` as the reverse proxy starting point.

## Local setup

Create and activate a virtual environment:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local environment file:

```bash
copy .env.example .env
```

Start PostgreSQL and Redis with Docker:

```bash
docker compose up -d postgres redis
```

Run Alembic migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/health
```

## Docker

Run the full local stack:

```bash
docker compose up --build
```

API:

```text
http://localhost:8000
```

Health route:

```text
GET /api/health
```

## Celery

Start a Celery worker locally:

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info
```

## Alembic

Create a migration after adding SQLAlchemy models:

```bash
alembic revision --autogenerate -m "create initial tables"
```

Apply migrations:

```bash
alembic upgrade head
```
