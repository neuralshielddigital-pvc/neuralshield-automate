import json
import time
import base64
import hashlib
import hmac
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.api.routes.agency_whop import router
from app.core.config import settings


def test_disabled_route_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings,'AGENCY_WHOP_ENABLED',False)
    app=FastAPI(); app.include_router(router)
    app.dependency_overrides[db_session]=lambda: object()
    assert TestClient(app).post('/webhooks/agency/whop',content=b'{}').status_code==404


def test_signature_precedes_processing_and_payload_limit(monkeypatch):
    monkeypatch.setattr(settings,'AGENCY_WHOP_ENABLED',True)
    monkeypatch.setattr(settings,'AGENCY_WHOP_ACCOUNT_ID','biz_test')
    monkeypatch.setattr(settings,'AGENCY_WHOP_WEBHOOK_SECRET','ws_test')
    monkeypatch.setattr('app.api.routes.agency_whop.configured_agency_whop_products',lambda:{'prod_test':'starter-toolkit'})
    calls=[]
    monkeypatch.setattr('app.api.routes.agency_whop.process_event',lambda *args: calls.append(args) or {'handled':True})
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[db_session]=lambda: object()
    client=TestClient(app)
    path='/webhooks/agency/whop'
    assert client.post(path,content=b'{}').status_code==400
    assert client.post(path,content=b'x'*65537).status_code==413
    assert calls==[]
    body=json.dumps({'id':'msg_test','type':'payment.succeeded','data':{'id':'pay_test'}}).encode()
    stamp=str(int(time.time()))
    signature=base64.b64encode(hmac.new(b'ws_test',b'msg_test.'+stamp.encode()+b'.'+body,hashlib.sha256).digest()).decode()
    headers={'webhook-id':'msg_test','webhook-timestamp':stamp,'webhook-signature':'v1,'+signature}
    assert client.post(path,content=body,headers=headers).status_code==200
    assert len(calls)==1
    headers['webhook-id']='msg_other'
    assert client.post(path,content=body,headers=headers).status_code==400
    assert len(calls)==1
