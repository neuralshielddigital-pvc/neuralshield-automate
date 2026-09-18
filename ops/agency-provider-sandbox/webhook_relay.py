"""Single-route local relay. No credentials, database or member files are loaded."""
import asyncio
import http.client
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

WEBHOOK_PATH = '/api/paddle/webhook'
MAX_BODY = 1_048_576


def forward_webhook(body, signature):
    # Fixed destination and path: never derive either from an incoming request.
    connection = http.client.HTTPConnection('api', 8097, timeout=4)
    try:
        connection.request('POST', WEBHOOK_PATH, body=body, headers={
            'Host': 'localhost', 'Content-Type': 'application/json',
            'Paddle-Signature': signature, 'Connection': 'close',
        })
        # Return only status; no upstream body, headers, redirects or cookies.
        return connection.getresponse().status
    finally:
        connection.close()


def create_app():
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def result(code, accepted=False):
        return JSONResponse({'received': accepted}, status_code=code,
                            headers={'Cache-Control': 'no-store',
                                     'X-Content-Type-Options': 'nosniff'})

    @app.middleware('http')
    async def webhook_only(request: Request, call_next):
        if (request.method != 'POST'
                or request.scope.get('raw_path') != WEBHOOK_PATH.encode()
                or request.scope.get('query_string')):
            return result(404)
        if request.headers.get('origin'):
            return result(403)
        if (request.headers.get('content-type', '').split(';')[0].strip().lower()
                != 'application/json'
                or request.headers.get('content-encoding', 'identity') != 'identity'):
            return result(415)
        signatures = request.headers.getlist('paddle-signature')
        if (len(signatures) != 1 or len(signatures[0]) > 4096
                or not re.fullmatch(r'ts=\d{1,12}(?:;h1=[0-9a-fA-F]{64})+', signatures[0])):
            return result(401)

        async def read_body():
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_BODY:
                    raise OverflowError
            return bytes(body)

        try:
            body = await asyncio.wait_for(read_body(), timeout=5)
            if not body:
                return result(400)
            status = await run_in_threadpool(forward_webhook, body, signatures[0])
        except OverflowError:
            return result(413)
        except asyncio.TimeoutError:
            return result(408)
        except Exception:
            # Do not print request data, signatures or provider/SQL exceptions.
            return result(502)
        if status == 200:
            return result(200, accepted=True)
        if status in (400, 401, 403, 413, 422, 429, 503):
            return result(status)
        return result(502)

    return app
