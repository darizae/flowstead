#!/usr/bin/env python3
"""Bounded real Flowstead Auth/API test. No passwords or tokens in diagnostics.

Run locally only. The two password files must be owner-owned 0600 regular files.
Credentials and JWTs remain in process memory, never disk, argv, tool output,
URL query parameters, HTTP error messages, logs or screenshots.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SUPABASE = "https://hkyobferqdfiicnsaupl.supabase.co"
API = "https://api.flowstead.darizae.dev/api/v1"
NAMES = (
    "flowstead-test-operator-a@example.invalid",
    "flowstead-test-operator-b@example.invalid",
)
ALLOWED = (
    {"plant-01", "plant-02"},
    {"plant-03", "plant-04", "plant-05"},
)
TIMEOUT = 12


class SmokeFailure(Exception):
    pass


def read_owner_only_password(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise SmokeFailure("Password source is not a regular file owned by current user")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise SmokeFailure("Password source is not private; chmod 600 first")
        if info.st_size < 8 or info.st_size > 4096:
            raise SmokeFailure("Password file has an invalid size")
        contents = os.read(fd, 4097)
        if len(contents) != info.st_size:
            raise SmokeFailure("Password file size changed while reading")
    finally:
        os.close(fd)
    try:
        text = contents.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError:
        raise SmokeFailure("Password is not UTF-8") from None
    if "\n" in text or "\r" in text or not text:
        raise SmokeFailure("Expected exactly one password per file")
    return text


def request_json(url: str, *, key: str = "", token: str = "",
                 payload: object | None = None, method: str = "GET") -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    if key:
        headers["apikey"] = key
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=TIMEOUT) as response:
            body = response.read(1024 * 1024)
            try:
                return response.status, json.loads(body)
            except (ValueError, UnicodeDecodeError):
                raise SmokeFailure("Non-JSON response from expected JSON endpoint") from None
    except HTTPError as error:
        # Never include response bodies, which might contain sensitive diagnostic content.
        return error.code, {}
    except (URLError, TimeoutError, OSError):
        raise SmokeFailure("TLS/network endpoint unavailable") from None


def login(email: str, password: str, key: str) -> str:
    status, body = request_json(
        SUPABASE + "/auth/v1/token?grant_type=password",
        key=key, payload={"email": email, "password": password}, method="POST"
    )
    if status != 200 or not isinstance(body, dict):
        raise SmokeFailure("Supabase test account login failed (HTTP " + str(status) + ")")
    token = body.get("access_token")
    user = body.get("user")
    if not isinstance(token, str) or token.count(".") != 2:
        raise SmokeFailure("Auth did not produce expected signed access token")
    if not isinstance(user, dict) or user.get("email") != email:
        raise SmokeFailure("Auth response identity mismatch")
    return token


def get_plants(token: str) -> set[str]:
    status, response = request_json(API + "/plants", token=token)
    if status != 200 or not isinstance(response, dict) or not isinstance(response.get("plants"), list):
        raise SmokeFailure("Private Plant list failed (HTTP " + str(status) + ")")
    return {item["plant_id"] for item in response["plants"]}


def expect_denied(url: str, token: str, label: str) -> None:
    status, _ = request_json(url, token=token)
    if status not in (403, 404):
        raise SmokeFailure(label + " returned unexpected HTTP " + str(status))
    print("PASS", label, "denied with", status)


def test_operator(index: int, token: str) -> None:
    ids = get_plants(token)
    if ids != ALLOWED[index]:
        raise SmokeFailure("Operator " + str(index + 1) + " sees incorrect Plant set")
    print("PASS operator", "A" if index == 0 else "B",
          "private Plant list:", ",".join(sorted(ids)))
    for plant in sorted(ids):
        status, _ = request_json(API + "/plants/" + plant + "/latest", token=token)
        if status != 200:
            raise SmokeFailure("Authorized latest denied")
    for plant in sorted(set().union(*ALLOWED) - ids):
        expect_denied(API + "/plants/" + plant + "/latest", token,
                      "operator " + ("A" if index == 0 else "B") + " other-Plant latest")
        expect_denied(API + "/plants/" + plant + "/report.pdf", token,
                      "operator " + ("A" if index == 0 else "B") + " other-Plant PDF")


def one_bounded_forecast(token_a: str, token_b: str) -> None:
    status, body = request_json(
        API + "/plants/plant-01/forecast-requests", token=token_a,
        payload={}, method="POST"
    )
    if status != 202 or not isinstance(body, dict):
        raise SmokeFailure("Authorized forecast POST returned HTTP " + str(status))
    job_id = body.get("correlation_id")
    if not isinstance(job_id, str) or len(job_id) > 80:
        raise SmokeFailure("Forecast request response missing job identifier")
    print("PASS exactly one bounded real forecast POST: HTTP 202")
    expect_denied(API + "/forecast-requests/" + job_id, token_b,
                  "operator B other-Plant forecast status")
    end = time.monotonic() + 55
    last = None
    while time.monotonic() < end:
        code, result = request_json(API + "/forecast-requests/" + job_id, token=token_a)
        if code != 200 or not isinstance(result, dict):
            raise SmokeFailure("Forecast status read failed (HTTP " + str(code) + ")")
        last = result.get("status")
        if last in ("completed", "failed"):
            break
        time.sleep(2)
    if last != "completed":
        raise SmokeFailure("Forecast job did not complete (terminal state: " + str(last) + ")")
    print("PASS worker completed real forecast job")
    code, forecast = request_json(API + "/plants/plant-01/forecast", token=token_a)
    if code != 200 or not isinstance(forecast, dict) or not isinstance(forecast.get("forecasts"), list):
        raise SmokeFailure("Persisted 12-hour forecast not accessible")
    hours = forecast["forecasts"]
    if len(hours) != 12 or [h.get("hour_number") for h in hours] != list(range(1, 13)):
        raise SmokeFailure("Persisted forecast has incorrect twelve-hour target set")
    print("PASS authorized 12-hour persisted forecast: 12 ordered hours")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--auth-only", action="store_true",
                        help="Verify Supabase credentials without contacting OCI API")
    parser.add_argument("--enqueue-one", action="store_true",
                        help="Create exactly one synthetic authorized forecast request")
    options = parser.parse_args()
    key = os.environ.get("FLOWSTEAD_SUPABASE_PUBLISHABLE_KEY", "")
    if not key.startswith("sb_publishable_"):
        raise SmokeFailure("Public publishable key missing from local environment")
    passwords = [
        read_owner_only_password(options.password_dir / (name + ".txt"))
        for name in NAMES
    ]
    tokens = [login(name, password, key) for name, password in zip(NAMES, passwords)]
    passwords.clear()
    print("PASS two real Supabase operator password logins; JWTs held in memory only")
    if options.auth_only:
        if options.enqueue_one:
            raise SmokeFailure("--auth-only cannot be combined with --enqueue-one")
        return
    for index, token in enumerate(tokens):
        test_operator(index, token)
    if options.enqueue_one:
        one_bounded_forecast(*tokens)
    print("PASS two test operators authenticated with actual Supabase JWTs and live API")


if __name__ == "__main__":
    try:
        main()
    except SmokeFailure as failure:
        # Messages are deliberately fixed by this script and never contain credentials.
        print("BLOCKED:", str(failure), file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print("BLOCKED: unexpected " + type(error).__name__ + " (details redacted)", file=sys.stderr)
        sys.exit(1)
