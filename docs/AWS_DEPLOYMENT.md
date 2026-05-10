# AWS EC2 Deployment Guide

This guide deploys NeuralShieldDigital on Ubuntu EC2 with FastAPI, PostgreSQL, Redis, Nginx, SSL, and Next.js.

## 1. Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm nginx redis-server postgresql-client git curl
sudo npm install -g n
sudo n 20
hash -r
```

## 2. Clone Project

```bash
sudo mkdir -p /opt/neuralshielddigital
sudo chown -R ubuntu:ubuntu /opt/neuralshielddigital
git clone https://github.com/YOUR_ORG/YOUR_REPO.git /opt/neuralshielddigital
cd /opt/neuralshielddigital
```

## 3. Configure Backend Environment

```bash
cd /opt/neuralshielddigital/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.production.example .env
nano .env
```

Set real values for `DATABASE_URL`, `SECRET_KEY`, `BACKEND_CORS_ORIGINS`, `TRUSTED_HOSTS`, Stripe keys, SMTP credentials, and frontend URLs.

## 4. Run Alembic Migrations

```bash
cd /opt/neuralshielddigital/backend
source .venv/bin/activate
alembic upgrade head
```

## 5. Create Admin User

```bash
cd /opt/neuralshielddigital/backend
source .venv/bin/activate
python scripts/create_admin.py \
  --email admin@example.com \
  --password 'Use-A-Strong-Password!123' \
  --tenant-name NeuralShieldDigital \
  --tenant-slug neuralshielddigital \
  --super-admin
```

## 6. Start Backend With Systemd

```bash
sudo cp /opt/neuralshielddigital/backend/neuralshielddigital-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable neuralshielddigital-backend
sudo systemctl start neuralshielddigital-backend
sudo systemctl status neuralshielddigital-backend
```

Check logs:

```bash
journalctl -u neuralshielddigital-backend -f
```

## 7. Configure Nginx Reverse Proxy

```bash
sudo cp /opt/neuralshielddigital/backend/nginx.conf.example /etc/nginx/sites-available/neuralshielddigital-api
sudo nano /etc/nginx/sites-available/neuralshielddigital-api
sudo ln -s /etc/nginx/sites-available/neuralshielddigital-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Point `api.example.com` DNS A record to the EC2 public IP.

## 8. Install SSL With Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
sudo certbot renew --dry-run
```

## 9. Deploy Frontend

```bash
cd /opt/neuralshielddigital/frontend-web
cp .env.production.example .env.production
nano .env.production
npm ci
npm run build
npm run start
```

For a persistent frontend process, create a separate systemd service or deploy the Next.js app to Vercel. Set `NEXT_PUBLIC_API_URL=https://api.example.com`.

## 10. Connect Domain

Create DNS records:

```text
api.example.com -> EC2 public IP
app.example.com -> frontend host
```

Update backend `.env`:

```text
BACKEND_CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=api.example.com,127.0.0.1,localhost
FRONTEND_SUCCESS_URL=https://app.example.com/dashboard/billing?success=true
FRONTEND_CANCEL_URL=https://app.example.com/dashboard/billing?canceled=true
```

Restart backend:

```bash
sudo systemctl restart neuralshielddigital-backend
```

## 11. Test Stripe Webhook

Set Stripe endpoint:

```text
https://api.example.com/api/stripe/webhook
```

Test with Stripe CLI:

```bash
stripe listen --forward-to https://api.example.com/api/stripe/webhook
stripe trigger checkout.session.completed
```

Check logs:

```bash
journalctl -u neuralshielddigital-backend -f
```

## 12. Health Checks

```bash
curl https://api.example.com/api/health
curl https://app.example.com/lead-form
```

Expected API health includes:

```json
{"status":"ok","database":"ok"}
```

## 13. Backups

```bash
cd /opt/neuralshielddigital/backend
source .env
bash scripts/backup_db.sh
```

Restore:

```bash
cd /opt/neuralshielddigital/backend
source .env
bash scripts/restore_db.sh /var/backups/neuralshielddigital/backup.dump
```

## 14. Restart Services

```bash
sudo systemctl restart neuralshielddigital-backend
sudo systemctl reload nginx
sudo systemctl restart redis-server
```
