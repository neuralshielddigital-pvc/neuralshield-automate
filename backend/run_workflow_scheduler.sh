#!/usr/bin/env bash
curl -s -X POST https://api.neuralshielddigital.com/api/admin/workflow-scheduler/run-due >/tmp/workflow_scheduler.log 2>&1
