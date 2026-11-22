"""Run the public Flowstead browser gate against an owned disposable database.

Orchestration CLI only; shared provisioning/build/auth primitives live in
``e2e_harness`` (audit #52). The 36-case Playwright suite in ``plants.spec.ts``
and the coverage contract are unchanged.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from e2e_harness import (
    RunnerError,
    create_database,
    drop_database,
    find_chromium_executable,
    mint_token,
    port_occupied,
    run,
    setup_test_auth,
    start_api,
    start_nats,
    start_worker,
    stop_nats,
    terminate,
    terminate_server,
    verify_m1,
    write_coverage_report,
)
from e2e_harness.m1 import SOURCE_SHA
from e2e_harness.proc import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=os.environ.get("FLOWSTEAD_M1_MANIFEST")
        or os.environ.get("M1_MANIFEST"),
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=os.environ.get("FLOWSTEAD_M1_DATA") or os.environ.get("M1_DATA"),
    )
    args = parser.parse_args()
    base_url = os.environ.get("DATABASE_URL")
    if not base_url:
        raise RunnerError("DATABASE_URL is required")
    if args.manifest is None or args.data is None:
        raise RunnerError("FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA are required")
    manifest_path = Path(args.manifest).resolve()
    data_path = Path(args.data).resolve()
    verify_m1(manifest_path, data_path)

    database_name: str | None = None
    nats_name: str | None = None
    worker_process: subprocess.Popen[bytes] | None = None
    api_process: subprocess.Popen[bytes] | None = None
    auth_server: http.server.HTTPServer | None = None
    previous_handlers: dict[int, object] = {}
    cleanup_started = False

    def request_shutdown(signum: int, _frame: object) -> None:
        if cleanup_started:
            return
        raise RunnerError(f"received signal {signum}; cleaning up owned E2E resources")

    try:
        if port_occupied(8000):
            raise RunnerError(
                "refusing to start E2E: 127.0.0.1:8000 is already occupied"
            )
        database_name, disposable_url = create_database(base_url)
        previous_handlers = {
            signum: signal.getsignal(signum)
            for signum in (signal.SIGINT, signal.SIGTERM)
        }
        for signum in previous_handlers:
            signal.signal(signum, request_shutdown)
        env = os.environ.copy()
        env["DATABASE_URL"] = disposable_url
        nats_name, nats_url = start_nats()
        env["NATS_URL"] = nats_url
        if (
            run(
                [
                    "uv",
                    "run",
                    "--project",
                    "backend",
                    "python",
                    "-m",
                    "backend.migrate",
                    "upgrade",
                ],
                env,
            )
            != 0
        ):
            raise RunnerError("Alembic migration failed")
        if (
            run(
                [
                    "uv",
                    "run",
                    "--project",
                    "backend",
                    "python",
                    "-m",
                    "backend.importer",
                    "--manifest",
                    str(manifest_path),
                    "--data",
                    str(data_path),
                    "--source-sha",
                    SOURCE_SHA,
                ],
                env,
            )
            != 0
        ):
            raise RunnerError("M1 import failed")
        # Build the deterministic 12-hour forecast so the forecast API returns
        # "available" 12-target points (otherwise it reports unavailable).
        if (
            run(
                [
                    "uv",
                    "run",
                    "--project",
                    "backend",
                    "python",
                    "-m",
                    "flowstead_api.forecast",
                ],
                env,
            )
            != 0
        ):
            raise RunnerError("forecast build failed")
        # Configure a deterministic local Supabase-compatible Auth authority and
        # seed the two disjoint test principals so the real FastAPI authorizes
        # test-principal RS256 JWTs during the browser gate.
        auth_setup = setup_test_auth(env, disposable_url)
        auth_server = auth_setup["server"]
        private_key = auth_setup["private_key"]
        env["FLOWSTEAD_TEST_PRINCIPAL_A_TOKEN"] = mint_token(
            private_key, "test-principal-a"
        )
        env["FLOWSTEAD_TEST_PRINCIPAL_B_TOKEN"] = mint_token(
            private_key, "test-principal-b"
        )
        env["FLOWSTEAD_TEST_PRINCIPAL_C_TOKEN"] = mint_token(
            private_key, "test-principal-c"
        )
        env["FLOWSTEAD_TEST_EXPIRED_TOKEN"] = mint_token(
            private_key, "test-principal-a", minutes=-30
        )
        env["FLOWSTEAD_TEST_ASSIGNMENTS"] = json.dumps(auth_setup["assignments"])
        worker_process = start_worker(env)
        api_process = start_api(env)
        # New browser runs write into an isolated artifact directory when
        # provided, instead of overwriting previously accepted Git evidence.
        evidence_directory = Path(
            os.environ.get("FLOWSTEAD_EVIDENCE_DIR") or ROOT / "docs/design/evidence"
        ).resolve()
        evidence_directory.mkdir(parents=True, exist_ok=True)
        e2e_env = env | {
            "PLAYWRIGHT_BASE_URL": "http://127.0.0.1:5173",
            "FLOWSTEAD_EVIDENCE_DIR": str(evidence_directory),
        }
        if (
            "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH" not in e2e_env
            or not e2e_env["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
        ):
            chromium_executable = find_chromium_executable()
            if chromium_executable:
                e2e_env["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = chromium_executable
        if (
            run(["pnpm", "--dir", "frontend", "run", "e2e"], e2e_env, timeout=300)
            != 0
        ):
            raise RunnerError("Playwright E2E failed")
        write_coverage_report(
            evidence_directory / "playwright-report" / "results.json",
            evidence_directory,
        )
        return 0
    finally:
        cleanup_started = True
        try:
            terminate_server(auth_server)
        finally:
            try:
                terminate(api_process)
            finally:
                try:
                    terminate(worker_process)
                finally:
                    try:
                        if nats_name is not None:
                            stop_nats(nats_name)
                    finally:
                        try:
                            if database_name is not None:
                                drop_database(database_name, base_url)
                        finally:
                            for signum, previous in previous_handlers.items():
                                signal.signal(signum, previous)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as error:
        print(f"E2E runner failed: {error}", file=sys.stderr)
        raise SystemExit(1)
