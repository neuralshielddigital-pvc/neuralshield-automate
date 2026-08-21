#!/usr/bin/env bash

set -u

FRONTEND_URL="${FRONTEND_URL:-https://app.neuralshielddigital.com}"
API_URL="${API_URL:-https://api.neuralshielddigital.com}"
BACKEND_DIR="${BACKEND_DIR:-/home/ubuntu/apps/automate/backend}"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf 'PASS  %s\n' "$1"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf 'FAIL  %s\n' "$1"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf 'WARN  %s\n' "$1"
}

check_status() {
    local name="$1"
    local expected="$2"
    local url="$3"
    shift 3

    local actual
    actual=$(
        curl \
            --silent \
            --show-error \
            --output /dev/null \
            --write-out '%{http_code}' \
            --connect-timeout 10 \
            --max-time 30 \
            "$@" \
            "$url" 2>/dev/null
    )
    local curl_exit=$?

    if [[ $curl_exit -ne 0 ]]; then
        fail "${name} — request failed"
        return
    fi

    if [[ "$actual" == "$expected" ]]; then
        pass "${name} — HTTP ${actual}"
    else
        fail "${name} — expected HTTP ${expected}, got HTTP ${actual}"
    fi
}

check_header() {
    local name="$1"
    local url="$2"
    local header_name="$3"
    local expected_value="$4"

    local headers
    headers=$(
        curl \
            --silent \
            --show-error \
            --head \
            --connect-timeout 10 \
            --max-time 30 \
            "$url" 2>/dev/null
    )
    local curl_exit=$?

    if [[ $curl_exit -ne 0 ]]; then
        fail "${name} — request failed"
        return
    fi

    if printf '%s\n' "$headers" |
        tr -d '\r' |
        grep -Eiq "^${header_name}:[[:space:]]*${expected_value}"; then
        pass "${name}"
    else
        fail "${name} — expected ${header_name}: ${expected_value}"
    fi
}

check_body_contains() {
    local name="$1"
    local url="$2"
    local expected="$3"

    local body
    body=$(
        curl \
            --silent \
            --show-error \
            --connect-timeout 10 \
            --max-time 30 \
            "$url" 2>/dev/null
    )
    local curl_exit=$?

    if [[ $curl_exit -ne 0 ]]; then
        fail "${name} — request failed"
        return
    fi

    if printf '%s' "$body" | grep -Fq "$expected"; then
        pass "${name}"
    else
        fail "${name} — expected content not found"
    fi
}

check_body_regex() {
    local name="$1"
    local url="$2"
    local expected_regex="$3"

    local body
    body=$(
        curl \
            --silent \
            --show-error \
            --connect-timeout 10 \
            --max-time 30 \
            "$url" 2>/dev/null
    )
    local curl_exit=$?

    if [[ $curl_exit -ne 0 ]]; then
        fail "${name} — request failed"
        return
    fi

    if printf '%s' "$body" | grep -Eiq "$expected_regex"; then
        pass "${name}"
    else
        fail "${name} — expected content not found"
    fi
}

check_systemd_service() {
    local name="$1"
    local service="$2"

    if systemctl is-active --quiet "$service"; then
        pass "${name} — active"
    else
        fail "${name} — inactive"
    fi
}

check_pm2_service() {
    local name="$1"
    local process_name="$2"

    if ! command -v pm2 >/dev/null 2>&1; then
        fail "${name} — pm2 command not found"
        return
    fi

    local status
    status=$(
        pm2 jlist 2>/dev/null |
        python3 -c '
import json
import sys

process_name = sys.argv[1]

try:
    processes = json.load(sys.stdin)
except Exception:
    raise SystemExit(1)

for process in processes:
    if process.get("name") == process_name:
        print(
            process.get("pm2_env", {}).get(
                "status",
                "",
            )
        )
        break
' "$process_name"
    )

    if [[ "$status" == "online" ]]; then
        pass "${name} — online"
    else
        fail "${name} — expected online, got ${status:-unknown}"
    fi
}

check_razorpay_configuration() {
    local env_file="${BACKEND_DIR}/.env"

    if [[ ! -f "$env_file" ]]; then
        fail "Razorpay configuration — backend .env not found"
        return
    fi

    local key_id
    local key_secret
    local currency

    key_id=$(
        sed -n 's/^RAZORPAY_KEY_ID=//p' "$env_file" |
        tail -1
    )

    key_secret=$(
        sed -n 's/^RAZORPAY_KEY_SECRET=//p' "$env_file" |
        tail -1
    )

    currency=$(
        sed -n 's/^RAZORPAY_CURRENCY=//p' "$env_file" |
        tail -1 |
        tr '[:lower:]' '[:upper:]'
    )

    if [[ -n "$key_id" && -n "$key_secret" ]]; then
        pass "Razorpay credentials are configured"
    else
        fail "Razorpay credentials are incomplete"
    fi

    if [[ "$key_id" == rzp_live_* ]]; then
        pass "Razorpay mode — live key configured"
    elif [[ "$key_id" == rzp_test_* ]]; then
        warn "Razorpay mode — test key configured"
    else
        fail "Razorpay mode — unrecognized key format"
    fi

    if [[ "$currency" == "USD" ]]; then
        pass "Razorpay currency — USD"
    elif [[ "$currency" == "INR" ]]; then
        warn "Razorpay currency — INR while public pricing is displayed in USD"
    elif [[ -n "$currency" ]]; then
        warn "Razorpay currency — ${currency}"
    else
        fail "Razorpay currency is not configured"
    fi
}


check_authenticated_auth_flow() {
    local email="${SMOKE_TEST_EMAIL:-}"
    local password="${SMOKE_TEST_PASSWORD:-}"

    if [[ -z "$email" || -z "$password" ]]; then
        warn "Authenticated auth flow — SMOKE_TEST_EMAIL/SMOKE_TEST_PASSWORD not configured"
        return
    fi

    local login_file
    local refresh_file
    local logout_file

    login_file=$(mktemp)
    refresh_file=$(mktemp)
    logout_file=$(mktemp)

    local login_payload
    login_payload=$(
        python3 - "$email" "$password" <<'PYJSON'
import json
import sys

print(
    json.dumps(
        {
            "email": sys.argv[1],
            "password": sys.argv[2],
        }
    )
)
PYJSON
    )

    local login_status
    login_status=$(
        curl \
            --silent \
            --show-error \
            --output "$login_file" \
            --write-out '%{http_code}' \
            --connect-timeout 10 \
            --max-time 30 \
            -X POST \
            -H "Content-Type: application/json" \
            --data "$login_payload" \
            "${API_URL}/api/auth/login" 2>/dev/null
    )
    local login_exit=$?

    if [[ $login_exit -ne 0 ]]; then
        fail "Authenticated login — request failed"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    if [[ "$login_status" != "200" ]]; then
        fail "Authenticated login — expected HTTP 200, got HTTP ${login_status}"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    local access_token
    local refresh_token
    local token_type
    local expires_in

    mapfile -t login_values < <(
        python3 - "$login_file" <<'PYJSON'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as file:
        data = json.load(file)
except Exception:
    raise SystemExit(1)

print(data.get("access_token", ""))
print(data.get("refresh_token", ""))
print(data.get("token_type", ""))
print(data.get("expires_in", ""))
PYJSON
    )

    access_token="${login_values[0]:-}"
    refresh_token="${login_values[1]:-}"
    token_type="${login_values[2]:-}"
    expires_in="${login_values[3]:-}"

    if [[ -z "$access_token" || -z "$refresh_token" ]]; then
        fail "Authenticated login — token fields missing"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    if [[ "$token_type" != "bearer" ]]; then
        fail "Authenticated login — unexpected token type"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    if ! [[ "$expires_in" =~ ^[0-9]+$ ]] || [[ "$expires_in" -le 0 ]]; then
        fail "Authenticated login — invalid expires_in"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    pass "Authenticated login and token response"

    local refresh_payload
    refresh_payload=$(
        python3 - "$refresh_token" <<'PYJSON'
import json
import sys

print(json.dumps({"refresh_token": sys.argv[1]}))
PYJSON
    )

    local refresh_status
    refresh_status=$(
        curl \
            --silent \
            --show-error \
            --output "$refresh_file" \
            --write-out '%{http_code}' \
            --connect-timeout 10 \
            --max-time 30 \
            -X POST \
            -H "Content-Type: application/json" \
            --data "$refresh_payload" \
            "${API_URL}/api/auth/refresh" 2>/dev/null
    )
    local refresh_exit=$?

    if [[ $refresh_exit -ne 0 ]]; then
        fail "Refresh token flow — request failed"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    if [[ "$refresh_status" != "200" ]]; then
        fail "Refresh token flow — expected HTTP 200, got HTTP ${refresh_status}"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    local refreshed_access_token
    local refreshed_refresh_token

    mapfile -t refresh_values < <(
        python3 - "$refresh_file" <<'PYJSON'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as file:
        data = json.load(file)
except Exception:
    raise SystemExit(1)

print(data.get("access_token", ""))
print(data.get("refresh_token", ""))
PYJSON
    )

    refreshed_access_token="${refresh_values[0]:-}"
    refreshed_refresh_token="${refresh_values[1]:-}"

    if [[ -z "$refreshed_access_token" || -z "$refreshed_refresh_token" ]]; then
        fail "Refresh token flow — refreshed tokens missing"
        rm -f "$login_file" "$refresh_file" "$logout_file"
        return
    fi

    pass "Refresh token flow"

    local logout_payload
    logout_payload=$(
        python3 - "$refreshed_refresh_token" <<'PYJSON'
import json
import sys

print(json.dumps({"refresh_token": sys.argv[1]}))
PYJSON
    )

    local logout_status
    logout_status=$(
        curl \
            --silent \
            --show-error \
            --output "$logout_file" \
            --write-out '%{http_code}' \
            --connect-timeout 10 \
            --max-time 30 \
            -X POST \
            -H "Content-Type: application/json" \
            --data "$logout_payload" \
            "${API_URL}/api/auth/logout" 2>/dev/null
    )
    local logout_exit=$?

    if [[ $logout_exit -ne 0 ]]; then
        fail "Logout flow — request failed"
    elif [[ "$logout_status" == "200" ]]; then
        pass "Logout flow"
    else
        fail "Logout flow — expected HTTP 200, got HTTP ${logout_status}"
    fi

    rm -f "$login_file" "$refresh_file" "$logout_file"
}

check_json_ld() {
    local url="$1"

    local result
    result=$(
        curl \
            --silent \
            --show-error \
            --connect-timeout 10 \
            --max-time 30 \
            "$url" |
        python3 -c '
import json
import sys
from html.parser import HTMLParser

class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.current = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if (
            tag == "script"
            and attrs.get("type")
            == "application/ld+json"
        ):
            self.capture = True
            self.current = []

    def handle_data(self, data):
        if self.capture:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.capture:
            self.blocks.append(
                "".join(self.current)
            )
            self.capture = False
            self.current = []

parser = JsonLdParser()
parser.feed(sys.stdin.read())

if not parser.blocks:
    print("FAILED: JSON-LD script not found")
    raise SystemExit(1)

data = json.loads(parser.blocks[0])
graph = data.get("@graph", [])

types = {
    item.get("@type")
    for item in graph
}

required = {
    "Organization",
    "WebSite",
    "SoftwareApplication",
    "FAQPage",
}

missing = required - types

if missing:
    print(
        "FAILED: missing "
        + ", ".join(sorted(missing))
    )
    raise SystemExit(1)

faq = next(
    (
        item
        for item in graph
        if item.get("@type") == "FAQPage"
    ),
    {},
)

questions = faq.get("mainEntity", [])

if len(questions) != 6:
    print(
        "FAILED: expected 6 FAQ questions, got "
        + str(len(questions))
    )
    raise SystemExit(1)

print("PASS")
' 2>/dev/null
    )
    local validation_exit=$?

    if [[ $validation_exit -eq 0 && "$result" == "PASS" ]]; then
        pass "Homepage structured data"
    else
        fail "Homepage structured data — ${result:-validation failed}"
    fi
}

printf '\nNeuralShieldDigital Launch QA Smoke Test\n'
printf 'Frontend: %s\n' "$FRONTEND_URL"
printf 'API:      %s\n\n' "$API_URL"

printf '%s\n' '=== Public Pages ==='

check_status "Landing page" "200" "${FRONTEND_URL}/"
check_status "Contact page" "200" "${FRONTEND_URL}/contact"
check_status "Privacy page" "200" "${FRONTEND_URL}/privacy"
check_status "Terms page" "200" "${FRONTEND_URL}/terms"
check_status "Login page" "200" "${FRONTEND_URL}/login"
check_status "Signup page" "200" "${FRONTEND_URL}/signup"
check_status "Forgot-password page" "200" "${FRONTEND_URL}/forgot-password"
check_status "Robots file" "200" "${FRONTEND_URL}/robots.txt"
check_status "Sitemap file" "200" "${FRONTEND_URL}/sitemap.xml"

printf '\n%s\n' '=== SEO / AEO ==='

check_body_contains \
    "Homepage title metadata" \
    "${FRONTEND_URL}/" \
    "NeuralShieldDigital | AI Automation Platform"

check_body_contains \
    "Homepage Open Graph metadata" \
    "${FRONTEND_URL}/" \
    'property="og:title"'

check_body_contains \
    "Homepage Twitter Card metadata" \
    "${FRONTEND_URL}/" \
    'name="twitter:card"'

check_body_contains \
    "Robots references sitemap" \
    "${FRONTEND_URL}/robots.txt" \
    "${FRONTEND_URL}/sitemap.xml"

check_body_contains \
    "Sitemap contains homepage" \
    "${FRONTEND_URL}/sitemap.xml" \
    "<loc>${FRONTEND_URL}</loc>"

check_body_contains \
    "Sitemap contains contact page" \
    "${FRONTEND_URL}/sitemap.xml" \
    "<loc>${FRONTEND_URL}/contact</loc>"

check_body_regex \
    "Dashboard noindex" \
    "${FRONTEND_URL}/dashboard" \
    'name="robots"[[:space:]]+content="noindex, nofollow"'

check_body_regex \
    "Admin noindex" \
    "${FRONTEND_URL}/admin" \
    'name="robots"[[:space:]]+content="noindex, nofollow"'

check_json_ld "${FRONTEND_URL}/"

printf '\n%s\n' '=== Backend / Authentication ==='

check_status \
    "Backend health" \
    "200" \
    "${API_URL}/api/health"

check_status \
    "Workflow templates catalog" \
    "200" \
    "${API_URL}/api/workflow-templates"

check_status \
    "Protected workflows reject missing JWT" \
    "401" \
    "${API_URL}/api/workflows"

check_status \
    "API v1 rejects missing API key" \
    "401" \
    "${API_URL}/api/v1/me"

check_status \
    "API v1 rejects invalid API key" \
    "401" \
    "${API_URL}/api/v1/me" \
    -H "Authorization: Bearer nsd_invalid_smoke_test_key"

check_status \
    "Admin route rejects unauthenticated request" \
    "401" \
    "${API_URL}/api/admin/workflow-runs"


printf '\n%s\n' '=== Authenticated Authentication Flow ==='

check_authenticated_auth_flow

printf '\n%s\n' '=== Security Headers ==='

check_header \
    "Frontend X-Content-Type-Options header" \
    "${FRONTEND_URL}/" \
    "x-content-type-options" \
    "nosniff"

check_header \
    "Frontend X-Frame-Options header" \
    "${FRONTEND_URL}/" \
    "x-frame-options" \
    "DENY"

check_header \
    "Frontend Referrer-Policy header" \
    "${FRONTEND_URL}/" \
    "referrer-policy" \
    "strict-origin-when-cross-origin"

check_header \
    "API X-Content-Type-Options header" \
    "${API_URL}/api/health" \
    "x-content-type-options" \
    "nosniff"

check_header \
    "API X-Frame-Options header" \
    "${API_URL}/api/health" \
    "x-frame-options" \
    "DENY"

printf '\n%s\n' '=== Production Services ==='

check_systemd_service \
    "Nginx service" \
    "nginx"

check_systemd_service \
    "Backend service" \
    "neuralshield-backend"

check_pm2_service \
    "Frontend PM2 process" \
    "neuralshield-frontend"

printf '\n%s\n' '=== Razorpay Readiness ==='

check_razorpay_configuration

printf '\n----------------------------------------\n'
printf 'Passed:   %s\n' "$PASS_COUNT"
printf 'Warnings: %s\n' "$WARN_COUNT"
printf 'Failed:   %s\n' "$FAIL_COUNT"
printf '%s\n' '----------------------------------------'

if [[ $FAIL_COUNT -gt 0 ]]; then
    printf 'RESULT: FAILED\n'
    exit 1
fi

if [[ $WARN_COUNT -gt 0 ]]; then
    printf 'RESULT: PASSED WITH WARNINGS\n'
    exit 0
fi

printf 'RESULT: PASSED\n'
exit 0
