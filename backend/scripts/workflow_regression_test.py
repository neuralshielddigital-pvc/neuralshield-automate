#!/usr/bin/env python3

from __future__ import annotations

import getpass
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_URL = "https://api.neuralshielddigital.com"
REQUEST_TIMEOUT_SECONDS = 30


class RegressionFailure(RuntimeError):
    pass


@dataclass
class ApiResponse:
    status: int
    body: Any


def print_pass(message: str) -> None:
    print(f"PASS  {message}")


def print_fail(message: str) -> None:
    print(f"FAIL  {message}")


def print_info(message: str) -> None:
    print(f"INFO  {message}")


def decode_response(raw: bytes) -> Any:
    if not raw:
        return None

    text = raw.decode("utf-8", errors="replace")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> ApiResponse:
    headers = {
        "Accept": "application/json",
        "User-Agent": "NeuralShieldDigital-Workflow-Regression/1.0",
    }

    data: bytes | None = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return ApiResponse(
                status=response.status,
                body=decode_response(response.read()),
            )
    except HTTPError as exc:
        return ApiResponse(
            status=exc.code,
            body=decode_response(exc.read()),
        )
    except URLError as exc:
        raise RegressionFailure(
            f"Request failed for {method} {url}: {exc.reason}"
        ) from exc


def require_status(
    response: ApiResponse,
    expected: int | set[int],
    operation: str,
) -> None:
    expected_statuses = (
        {expected}
        if isinstance(expected, int)
        else expected
    )

    if response.status not in expected_statuses:
        raise RegressionFailure(
            f"{operation}: expected HTTP "
            f"{sorted(expected_statuses)}, got HTTP {response.status}; "
            f"response={response.body!r}"
        )


def require_dict(value: Any, operation: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegressionFailure(
            f"{operation}: expected JSON object, got {type(value).__name__}"
        )

    return value


def require_nonempty_string(
    data: dict[str, Any],
    field: str,
    operation: str,
) -> str:
    value = data.get(field)

    if not isinstance(value, str) or not value.strip():
        raise RegressionFailure(
            f"{operation}: missing or invalid '{field}'"
        )

    return value.strip()


def get_credentials() -> tuple[str, str]:
    email = os.environ.get("SMOKE_TEST_EMAIL", "").strip()
    password = os.environ.get("SMOKE_TEST_PASSWORD", "")

    if not email:
        email = input("Smoke test email: ").strip()

    if not password:
        password = getpass.getpass("Smoke test password: ")

    if not email or not password:
        raise RegressionFailure(
            "Smoke-test email and password are required."
        )

    return email, password


def normalize_status(value: Any) -> str:
    return str(value or "").strip().upper()


def main() -> int:
    api_url = os.environ.get(
        "API_URL",
        DEFAULT_API_URL,
    ).rstrip("/")

    email, password = get_credentials()

    access_token: str | None = None
    workflow_id: str | None = None
    workflow_deleted = False

    unique_suffix = uuid.uuid4().hex[:12]
    workflow_name = f"QA Regression {unique_suffix}"
    audit_action = f"qa.workflow.regression.{unique_suffix}"

    print()
    print("NeuralShieldDigital Workflow Regression Test")
    print(f"API: {api_url}")
    print()

    try:
        # 1. Login
        login_response = request_json(
            "POST",
            f"{api_url}/api/auth/login",
            payload={
                "email": email,
                "password": password,
            },
        )
        require_status(login_response, 200, "Login")

        login_body = require_dict(login_response.body, "Login")
        access_token = require_nonempty_string(
            login_body,
            "access_token",
            "Login",
        )
        print_pass("Authenticated login")

        # 2. Create isolated temporary workflow
        create_payload = {
            "name": workflow_name,
            "description": (
                "Temporary automated workflow regression test. "
                "Safe to delete."
            ),
            "is_active": True,
            "schedule_enabled": False,
            "schedule_cron": None,
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {},
            },
            "actions": [
                {
                    "type": "ADD_AUDIT_LOG",
                    "config": {
                        "action": audit_action,
                    },
                }
            ],
        }

        create_response = request_json(
            "POST",
            f"{api_url}/api/workflows",
            payload=create_payload,
            token=access_token,
        )
        require_status(create_response, 201, "Create workflow")

        create_body = require_dict(
            create_response.body,
            "Create workflow",
        )
        workflow_id = require_nonempty_string(
            create_body,
            "id",
            "Create workflow",
        )

        if create_body.get("name") != workflow_name:
            raise RegressionFailure(
                "Create workflow: returned workflow name does not match."
            )

        if create_body.get("is_active") is not True:
            raise RegressionFailure(
                "Create workflow: workflow was not returned as active."
            )

        print_pass("Temporary workflow created")

        # 3. Read workflow
        get_response = request_json(
            "GET",
            f"{api_url}/api/workflows/{workflow_id}",
            token=access_token,
        )
        require_status(get_response, 200, "Read workflow")

        get_body = require_dict(get_response.body, "Read workflow")

        if str(get_body.get("id")) != workflow_id:
            raise RegressionFailure(
                "Read workflow: returned workflow ID does not match."
            )

        print_pass("Temporary workflow retrieval")

        # 4. Execute workflow
        run_payload = {
            "source": "workflow_regression_test",
            "regression_id": unique_suffix,
            "safe_test": True,
        }

        run_response = request_json(
            "POST",
            f"{api_url}/api/workflows/{workflow_id}/run",
            payload=run_payload,
            token=access_token,
        )
        require_status(run_response, 200, "Manual workflow run")

        run_body = require_dict(
            run_response.body,
            "Manual workflow run",
        )
        run_id = require_nonempty_string(
            run_body,
            "id",
            "Manual workflow run",
        )

        run_status = normalize_status(run_body.get("status"))

        if run_status != "COMPLETED":
            raise RegressionFailure(
                "Manual workflow run: expected COMPLETED, "
                f"got {run_status or 'missing status'}; "
                f"response={run_body!r}"
            )

        logs = run_body.get("logs")
        if not isinstance(logs, dict):
            raise RegressionFailure(
                "Manual workflow run: logs object is missing."
            )

        steps = logs.get("steps")
        if not isinstance(steps, list) or not steps:
            raise RegressionFailure(
                "Manual workflow run: execution steps are missing."
            )

        matching_steps = [
            step
            for step in steps
            if isinstance(step, dict)
            and step.get("action") == "ADD_AUDIT_LOG"
        ]

        if not matching_steps:
            raise RegressionFailure(
                "Manual workflow run: ADD_AUDIT_LOG step not found."
            )

        action_result = matching_steps[0].get("result")
        if (
            not isinstance(action_result, dict)
            or not action_result.get("audit_log_id")
        ):
            raise RegressionFailure(
                "Manual workflow run: audit_log_id is missing."
            )

        print_pass("Workflow executed with COMPLETED status")
        print_pass("ADD_AUDIT_LOG execution result")

        # 5. Verify run in history
        history_response = request_json(
            "GET",
            (
                f"{api_url}/api/workflows/{workflow_id}/runs"
                "?page=1&page_size=25"
            ),
            token=access_token,
        )
        require_status(history_response, 200, "List workflow runs")

        history_body = require_dict(
            history_response.body,
            "List workflow runs",
        )
        history_items = history_body.get("items")

        if not isinstance(history_items, list):
            raise RegressionFailure(
                "List workflow runs: items list is missing."
            )

        matching_runs = [
            item
            for item in history_items
            if isinstance(item, dict)
            and str(item.get("id")) == run_id
        ]

        if not matching_runs:
            raise RegressionFailure(
                "List workflow runs: newly created run was not found."
            )

        history_status = normalize_status(
            matching_runs[0].get("status")
        )

        if history_status != "COMPLETED":
            raise RegressionFailure(
                "List workflow runs: expected COMPLETED status, "
                f"got {history_status or 'missing status'}."
            )

        print_pass("Workflow run history verification")

        # 6. Delete temporary workflow
        delete_response = request_json(
            "DELETE",
            f"{api_url}/api/workflows/{workflow_id}",
            token=access_token,
        )
        require_status(delete_response, 204, "Delete workflow")
        workflow_deleted = True

        print_pass("Temporary workflow deleted")

        # 7. Confirm deletion
        deleted_get_response = request_json(
            "GET",
            f"{api_url}/api/workflows/{workflow_id}",
            token=access_token,
        )
        require_status(
            deleted_get_response,
            404,
            "Verify workflow deletion",
        )

        print_pass("Workflow deletion confirmed with HTTP 404")

        print()
        print("----------------------------------------")
        print("RESULT: PASSED")
        print("----------------------------------------")
        return 0

    except RegressionFailure as exc:
        print_fail(str(exc))

        print()
        print("----------------------------------------")
        print("RESULT: FAILED")
        print("----------------------------------------")
        return 1

    finally:
        # Best-effort cleanup if a test failed after workflow creation.
        if (
            workflow_id
            and access_token
            and not workflow_deleted
        ):
            print_info(
                "Attempting cleanup of temporary workflow..."
            )

            try:
                cleanup_response = request_json(
                    "DELETE",
                    f"{api_url}/api/workflows/{workflow_id}",
                    token=access_token,
                )

                if cleanup_response.status in {204, 404}:
                    print_info(
                        "Temporary workflow cleanup completed."
                    )
                else:
                    print_fail(
                        "Temporary workflow cleanup failed with "
                        f"HTTP {cleanup_response.status}."
                    )
            except Exception as cleanup_exc:
                print_fail(
                    "Temporary workflow cleanup encountered an "
                    f"error: {cleanup_exc}"
                )


if __name__ == "__main__":
    sys.exit(main())
