"""Run offline-provider Agency tests against an explicitly isolated PostgreSQL DB."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    from sqlalchemy.engine import make_url
    raw = os.environ.get('AGENCY_TEST_DATABASE_URL', '')
    try:
        url = make_url(raw)
        valid = (url.drivername == 'postgresql+psycopg'
                 and url.host in ('127.0.0.1', '::1')
                 and (url.database or '').startswith('nsd_agency_test_')
                 and not url.query
                 and os.environ.get('AGENCY_TEST_ALLOW_ISOLATED_POSTGRES') == 'yes')
    except Exception:
        valid = False
    if not valid:
        print('BLOCKED: configure and confirm an isolated loopback nsd_agency_test_ PostgreSQL database; no connection attempted.')
        return 2
    # Prevent unrelated runtime configuration from contacting external services.
    env = os.environ.copy()
    env.update(ENVIRONMENT='test', AUTOMATION_BACKGROUND_WORKER_ENABLED='false',
               AGENCY_STARTER_DELIVERY_ENABLED='false',
               DATABASE_URL=raw,
               SECRET_KEY='synthetic-isolated-agency-validation-only-key')
    root = Path(__file__).resolve().parents[1]
    print('Running PostgreSQL tests with disposable per-test schemas and fake Paddle/SMTP providers.')
    # Do not echo the database URL, credentials or provider environment.
    return subprocess.run([sys.executable, '-m', 'pytest',
        'tests/test_agency_automatic_delivery.py', '-q', '-o', 'addopts=', '--tb=short',
        '--disable-warnings'], cwd=root / 'backend', env=env).returncode


if __name__ == '__main__':
    raise SystemExit(main())
