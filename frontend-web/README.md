# NeuralShieldDigital Frontend

Next.js frontend for the FastAPI SaaS backend.

## Setup

```bash
cd frontend-web
copy .env.example .env.local
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

Backend expected at:

```text
http://127.0.0.1:8000
```

## Production build

Create production environment:

```bash
cp .env.production.example .env.production
```

Set:

```text
NEXT_PUBLIC_API_URL=https://api.example.com
```

Build and start:

```bash
npm ci
npm run build
npm run start
```

## Implemented pages

```text
/login
/signup
/dashboard
/dashboard/billing
/admin
/lead-form
```

For local development, auth tokens are stored in `localStorage`. Use secure HTTP-only cookies before production launch.
