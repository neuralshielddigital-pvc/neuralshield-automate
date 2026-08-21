#!/bin/bash
set -e

echo "1) Python compile check..."
python3 -m py_compile app/services/workflow_service.py

echo "2) Indentation/tab check..."
python3 -m tabnanny app/services/workflow_service.py

echo "3) Restart backend..."
sudo systemctl reset-failed neuralshield-backend
sudo systemctl restart neuralshield-backend

echo "4) Health check..."
sleep 2
curl http://127.0.0.1:8000/api/health

echo ""
echo "✅ Backend safe restart complete"
