# NeuralShieldDigital Production Rollback Guide

Use this guide when a production deployment causes errors, failed health checks, broken frontend behavior, backend failures, database migration problems, payment configuration issues, or Nginx errors.

## 1. Production Paths and Services

### Frontend

Repository:

```text
/home/ubuntu/apps/automate/frontend-web
```

PM2 process:

```text
neuralshield-frontend
```

Public URL:

```text
https://app.neuralshielddigital.com
```

### Backend

Repository:

```text
/home/ubuntu/apps/automate/backend
```

Systemd service:

```text
neuralshield-backend
```

Public URL:

```text
https://api.neuralshielddigital.com
```

### Infrastructure

* AWS EC2 Ubuntu
* Nginx
* Cloudflare
* Neon PostgreSQL
* PM2
* Systemd

## 2. Immediate Incident Checks

Before changing anything, record the current time and environment:

```bash
date
whoami
pwd
```

Check service status:

```bash
pm2 status neuralshield-frontend

sudo systemctl status neuralshield-backend --no-pager

sudo systemctl status nginx --no-pager
```

Check public endpoints:

```bash
curl -I https://app.neuralshielddigital.com/

curl -i https://api.neuralshielddigital.com/api/health
```

Check recent logs:

```bash
pm2 logs neuralshield-frontend --lines 100 --nostream
```

```bash
sudo journalctl \
  -u neuralshield-backend \
  -n 150 \
  --no-pager
```

```bash
sudo journalctl \
  -u nginx \
  -n 100 \
  --no-pager
```

## 3. Frontend Rollback

Frontend path:

```bash
cd /home/ubuntu/apps/automate/frontend-web
```

### Restore a Single Frontend File

List available backups:

```bash
find backups -type f | sort
```

Restore only the affected file:

```bash
cp backups/<backup-folder>/<backup-file> \
app/<target-file>
```

Build:

```bash
npm run build
```

Restart frontend:

```bash
pm2 restart neuralshield-frontend
pm2 status neuralshield-frontend
```

Verify:

```bash
curl -I https://app.neuralshielddigital.com/
```

### Rebuild Frontend from Clean Build Cache

If source files are correct but the current build is broken:

```bash
cd /home/ubuntu/apps/automate/frontend-web

rm -rf .next

npm run build

pm2 restart neuralshield-frontend
```

Check logs:

```bash
pm2 logs neuralshield-frontend --lines 100 --nostream
```

Verify:

```bash
curl -I https://app.neuralshielddigital.com/
```

### PM2 Recovery

Check PM2 processes:

```bash
pm2 list
```

If the process exists but is stopped:

```bash
pm2 restart neuralshield-frontend
```

After recovery:

```bash
pm2 save
pm2 status neuralshield-frontend
```

Do not invent a new PM2 start command during an incident unless the existing production start configuration has been confirmed.

## 4. Backend Rollback

Backend path:

```bash
cd /home/ubuntu/apps/automate/backend
```

### Restore a Single Backend File

List backend backup files:

```bash
find app -type f -name "*.backup*" | sort
```

List backup directories:

```bash
find backups -type f 2>/dev/null | sort
```

Restore the affected file:

```bash
cp <backup-file> <target-file>
```

Compile backend:

```bash
python3 -m compileall app
```

Restart backend:

```bash
sudo systemctl restart neuralshield-backend
```

Check status:

```bash
sudo systemctl status neuralshield-backend --no-pager
```

Verify public health:

```bash
curl -i https://api.neuralshielddigital.com/api/health
```

### Backend Failure Diagnosis

Check backend logs:

```bash
sudo journalctl \
  -u neuralshield-backend \
  -n 200 \
  --no-pager
```

Check local backend health:

```bash
curl -i http://127.0.0.1:8000/api/health
```

Check public backend health:

```bash
curl -i https://api.neuralshielddigital.com/api/health
```

If local health works but public health fails, inspect Nginx and Cloudflare before changing backend code.

## 5. Database Rollback

Database changes are high-risk operations.

Before any database rollback:

```bash
cd /home/ubuntu/apps/automate/backend
```

Check current migration state:

```bash
alembic current
```

Check migration heads:

```bash
alembic heads
```

Check migration history:

```bash
alembic history --verbose | head -80
```

### Important Database Rule

Do not run:

```bash
alembic downgrade
```

unless all of these are true:

* The exact previous revision is known.
* The migration downgrade path has been reviewed.
* A recent database backup exists.
* Destructive data loss has been ruled out.
* Production rollback has been explicitly approved.

### Create Emergency Database Backup

Use the backend backup script:

```bash
/home/ubuntu/apps/automate/backend/scripts/backup_db.sh
```

Or the active server backup script:

```bash
/home/ubuntu/scripts/db-backup.sh
```

Confirm latest backups:

```bash
find /home/ubuntu \
  -type f \
  \( -name "*.sql" -o -name "*.dump" -o -name "*.gz" \) \
  -printf '%TY-%Tm-%Td %TH:%TM %p\n' \
  2>/dev/null \
  | sort -r \
  | head -20
```

### Database Restore

Restore script:

```text
/home/ubuntu/apps/automate/backend/scripts/restore_db.sh
```

Read the restore script before running it:

```bash
sed -n '1,260p' \
/home/ubuntu/apps/automate/backend/scripts/restore_db.sh
```

Before restore:

1. Confirm the target database.
2. Confirm the backup filename.
3. Confirm the backup is valid.
4. Stop unnecessary write activity.
5. Create one additional emergency backup.
6. Confirm that restore will not overwrite the wrong database.
7. Restore only after explicit production approval.

## 6. Nginx Rollback

Before modifying Nginx:

```bash
sudo nginx -t
```

List configuration files:

```bash
sudo find /etc/nginx \
  -maxdepth 3 \
  -type f \
  | sort
```

Restore a known-good configuration:

```bash
sudo cp <nginx-backup-file> <nginx-target-file>
```

Validate configuration:

```bash
sudo nginx -t
```

Reload only after validation passes:

```bash
sudo systemctl reload nginx
```

Check Nginx status:

```bash
sudo systemctl status nginx --no-pager
```

Verify frontend and backend:

```bash
curl -I https://app.neuralshielddigital.com/
```

```bash
curl -i https://api.neuralshielddigital.com/api/health
```

Never reload Nginx after a failed:

```bash
sudo nginx -t
```

## 7. Environment Variable Rollback

Backend environment file:

```text
/home/ubuntu/apps/automate/backend/.env
```

Frontend environment files may include:

```text
/home/ubuntu/apps/automate/frontend-web/.env.local
/home/ubuntu/apps/automate/frontend-web/.env.production
```

### Backup Environment File

Before changing backend environment variables:

```bash
cd /home/ubuntu/apps/automate/backend

cp .env ".env.backup-$(date +%Y%m%d-%H%M%S)"
```

Before changing frontend environment variables:

```bash
cd /home/ubuntu/apps/automate/frontend-web

cp .env.production \
".env.production.backup-$(date +%Y%m%d-%H%M%S)"
```

Never print full production secrets in:

* Chat messages
* Screenshots
* Tickets
* Logs
* Public repositories
* Documentation

After backend environment changes:

```bash
sudo systemctl restart neuralshield-backend
```

After frontend environment changes:

```bash
cd /home/ubuntu/apps/automate/frontend-web

npm run build

pm2 restart neuralshield-frontend --update-env
```

## 8. Razorpay Emergency Rollback

If live Razorpay activation causes checkout or subscription failures:

1. Do not delete Payment records manually.
2. Do not delete Subscription records manually.
3. Preserve Razorpay order IDs.
4. Preserve Razorpay payment IDs.
5. Preserve webhook event details.
6. Preserve audit logs.
7. Restore the previous backend `.env`.
8. Restart the backend.
9. Verify billing page still loads.
10. Run the production smoke test.

Restore previous environment file:

```bash
cd /home/ubuntu/apps/automate/backend

cp .env.backup-<timestamp> .env
```

Restart backend:

```bash
sudo systemctl restart neuralshield-backend
```

Verify backend:

```bash
curl -i https://api.neuralshielddigital.com/api/health
```

Run smoke test:

```bash
cd /home/ubuntu/apps/automate/backend

./scripts/production_smoke_test.sh
```

If payment problems affect customers, temporarily disable checkout only if required. Do not remove historical payment data.

## 9. Full Service Recovery

Restart services in this order:

```bash
sudo systemctl restart neuralshield-backend
```

```bash
sudo systemctl restart nginx
```

```bash
pm2 restart neuralshield-frontend
```

Check status:

```bash
sudo systemctl status neuralshield-backend --no-pager
```

```bash
sudo systemctl status nginx --no-pager
```

```bash
pm2 status neuralshield-frontend
```

Run public health checks:

```bash
curl -I https://app.neuralshielddigital.com/
```

```bash
curl -i https://api.neuralshielddigital.com/api/health
```

Run production smoke test:

```bash
cd /home/ubuntu/apps/automate/backend

./scripts/production_smoke_test.sh
```

Required result:

```text
Failed: 0
```

## 10. Post-Rollback Validation

After every rollback, confirm:

* Frontend returns HTTP 200.
* Backend health returns HTTP 200.
* Nginx is active.
* Backend systemd service is active.
* Frontend PM2 process is online.
* Login page loads.
* Signup page loads.
* Dashboard loads after authentication.
* Admin access works for authorized users.
* Protected APIs reject unauthenticated users.
* Workflows can be listed.
* Existing workflows still run.
* No critical errors appear in logs.
* Production smoke test has zero failures.
* Database backup exists.
* Restored files are documented.

## 11. Incident Record

Record the following:

* Incident date and time
* Affected service
* Customer impact
* Failing deployment or change
* Error messages
* Files restored
* Environment changes
* Database actions
* Commands executed
* Smoke-test result
* Root cause
* Corrective action
* Preventive action

Do not delete incident logs until the incident has been reviewed.

## 12. Production Safety Rules

* Create a backup before every modification.
* Restore only the affected component.
* Do not perform unnecessary refactoring during an incident.
* Do not expose secrets.
* Do not manually edit production database rows without a reviewed query.
* Do not run destructive migrations without a verified backup.
* Do not restore a database without confirming the target database.
* Do not reload Nginx unless `nginx -t` passes.
* Build the frontend before restarting PM2.
* Compile the backend before restarting systemd.
* Run the production smoke test after every rollback.
* Preserve payment, subscription, audit, and workflow history.
* Document every production rollback.
