"""Shared local E2E harness primitives (audit #52).

Extracted from the former 663-line ``run_local.py`` monolith: subprocess and
process-group lifecycle, M1 fixture verification, disposable database
provisioning, isolated NATS/JetStream, API/worker startup, the throwaway JWT
authority, Chromium resolution and coverage receipts. ``run_local.py`` keeps
the CLI and the E2E-specific orchestration.
"""

from .auth import mint_token, setup_test_auth, terminate_server
from .browser import find_chromium_executable
from .coverage_report import write_coverage_report
from .db import create_database, drop_database, loopback_url
from .m1 import verify_m1
from .nats import start_nats, stop_nats
from .proc import (
    RunnerError,
    add_repo_to_pythonpath,
    port_occupied,
    run,
    terminate,
)
from .services import start_api, start_worker

__all__ = [
    "RunnerError",
    "add_repo_to_pythonpath",
    "create_database",
    "drop_database",
    "find_chromium_executable",
    "loopback_url",
    "mint_token",
    "port_occupied",
    "run",
    "setup_test_auth",
    "start_api",
    "start_nats",
    "start_worker",
    "stop_nats",
    "terminate",
    "terminate_server",
    "verify_m1",
    "write_coverage_report",
]
