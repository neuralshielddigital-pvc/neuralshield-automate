from __future__ import annotations

import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import SplitResult, urlsplit, urlunsplit

import requests


ALLOWED_OUTBOUND_HTTP_METHODS = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE"}
)

MAX_OUTBOUND_URL_LENGTH = 2048
MAX_OUTBOUND_REQUEST_BODY_BYTES = 256 * 1024
MAX_OUTBOUND_RESPONSE_BODY_BYTES = 2 * 1024 * 1024

CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 15

BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home",
)

BLOCKED_REQUEST_HEADERS = frozenset(
    {
        "connection",
        "content-length",
        "host",
        "proxy-authorization",
        "proxy-connection",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


@dataclass(frozen=True)
class SafeHTTPResponse:
    status_code: int
    ok: bool
    text: str


def _is_blocked_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return True

    return not address.is_global


def _normalize_and_validate_url(raw_url: str) -> tuple[str, SplitResult]:
    if not isinstance(raw_url, str):
        raise ValueError("Outbound URL must be a string.")

    url = raw_url.strip()

    if not url:
        raise ValueError("Outbound URL cannot be empty.")

    if len(url) > MAX_OUTBOUND_URL_LENGTH:
        raise ValueError(
            f"Outbound URL exceeds {MAX_OUTBOUND_URL_LENGTH} characters."
        )

    try:
        parsed = urlsplit(url)
    except ValueError as error:
        raise ValueError("Outbound URL is malformed.") from error

    scheme = parsed.scheme.lower()

    if scheme not in {"http", "https"}:
        raise ValueError("Outbound URL must use http or https.")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Outbound URL credentials are not allowed.")

    if not parsed.hostname:
        raise ValueError("Outbound URL must include a hostname.")

    if parsed.fragment:
        raise ValueError("Outbound URL fragments are not allowed.")

    hostname = parsed.hostname.rstrip(".").lower()

    if hostname == "localhost" or hostname.endswith(BLOCKED_HOST_SUFFIXES):
        raise ValueError("Outbound URL hostname is not allowed.")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Outbound URL contains an invalid port.") from error

    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Outbound URL contains an invalid port.")

    normalized_host = hostname

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            normalized_host = hostname.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise ValueError(
                "Outbound URL hostname is invalid."
            ) from error
    else:
        if not literal_ip.is_global:
            raise ValueError(
                "Outbound URL resolves to a non-public IP address."
            )

        if literal_ip.version == 6:
            normalized_host = f"[{literal_ip.compressed}]"
        else:
            normalized_host = literal_ip.compressed

    normalized_netloc = normalized_host

    if port is not None:
        normalized_netloc = f"{normalized_host}:{port}"

    normalized = urlunsplit(
        (
            scheme,
            normalized_netloc,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )

    normalized_parsed = urlsplit(normalized)
    return normalized, normalized_parsed


def _resolve_and_validate_public_addresses(
    parsed: SplitResult,
) -> set[str]:
    hostname = parsed.hostname

    if not hostname:
        raise ValueError("Outbound URL hostname is missing.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        address_info = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as error:
        raise ValueError(
            "Outbound URL hostname could not be resolved."
        ) from error

    resolved_addresses = {
        item[4][0].split("%", 1)[0]
        for item in address_info
        if item[4]
    }

    if not resolved_addresses:
        raise ValueError(
            "Outbound URL hostname did not resolve to an address."
        )

    blocked_addresses = sorted(
        address
        for address in resolved_addresses
        if _is_blocked_ip(address)
    )

    if blocked_addresses:
        raise ValueError(
            "Outbound URL resolves to a non-public IP address."
        )

    return resolved_addresses


def _sanitize_headers(
    headers: Mapping[str, Any] | None,
) -> dict[str, str]:
    if headers is None:
        return {}

    if not isinstance(headers, Mapping):
        raise ValueError("Outbound HTTP headers must be an object.")

    sanitized: dict[str, str] = {}

    for raw_name, raw_value in headers.items():
        name = str(raw_name).strip()
        value = str(raw_value)

        if not name:
            raise ValueError("Outbound HTTP header name cannot be empty.")

        if "\r" in name or "\n" in name:
            raise ValueError("Outbound HTTP header name is invalid.")

        if "\r" in value or "\n" in value:
            raise ValueError("Outbound HTTP header value is invalid.")

        if name.lower() in BLOCKED_REQUEST_HEADERS:
            raise ValueError(
                f"Outbound HTTP header is not allowed: {name}"
            )

        sanitized[name] = value

    return sanitized


def _validate_request_body_size(
    json_body: Any,
    query_params: Mapping[str, Any] | None,
) -> None:
    candidate = query_params if query_params is not None else json_body

    if candidate is None:
        return

    try:
        encoded = json.dumps(
            candidate,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Outbound HTTP request body is not serializable."
        ) from error

    if len(encoded) > MAX_OUTBOUND_REQUEST_BODY_BYTES:
        raise ValueError(
            "Outbound HTTP request body exceeds the allowed size."
        )


def safe_outbound_request(
    *,
    method: str,
    url: str,
    headers: Mapping[str, Any] | None = None,
    json_body: Any = None,
    query_params: Mapping[str, Any] | None = None,
) -> SafeHTTPResponse:
    normalized_method = str(method).strip().upper()

    if normalized_method not in ALLOWED_OUTBOUND_HTTP_METHODS:
        raise ValueError(
            "Outbound HTTP method must be one of: "
            + ", ".join(sorted(ALLOWED_OUTBOUND_HTTP_METHODS))
            + "."
        )

    normalized_url, parsed = _normalize_and_validate_url(url)
    _resolve_and_validate_public_addresses(parsed)

    sanitized_headers = _sanitize_headers(headers)
    _validate_request_body_size(json_body, query_params)

    session = requests.Session()
    session.trust_env = False

    try:
        with session.request(
            method=normalized_method,
            url=normalized_url,
            headers=sanitized_headers,
            json=json_body,
            params=query_params,
            timeout=(
                CONNECT_TIMEOUT_SECONDS,
                READ_TIMEOUT_SECONDS,
            ),
            allow_redirects=False,
            stream=True,
        ) as response:
            body = response.raw.read(
                MAX_OUTBOUND_RESPONSE_BODY_BYTES + 1,
                decode_content=True,
            )

            if len(body) > MAX_OUTBOUND_RESPONSE_BODY_BYTES:
                raise ValueError(
                    "Outbound HTTP response exceeds the allowed size."
                )

            encoding = response.encoding or "utf-8"
            text = body.decode(encoding, errors="replace")

            return SafeHTTPResponse(
                status_code=response.status_code,
                ok=response.ok,
                text=text,
            )
    except requests.Timeout as error:
        raise ValueError("Outbound HTTP request timed out.") from error
    except requests.RequestException as error:
        raise ValueError("Outbound HTTP request failed.") from error
    finally:
        session.close()


def sanitized_url_for_result(raw_url: str) -> str:
    normalized_url, parsed = _normalize_and_validate_url(raw_url)

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            "",
            "",
        )
    )
