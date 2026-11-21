"""Keep the owner-selected existing OCI micro target in checked-in contracts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_existing_host_contract_has_no_replacement_machine() -> None:
    paths = [
        ROOT / "docs/deployment/OCI_ALWAYS_FREE.md",
        ROOT / "docs/deployment/HOSTED_DEPLOYMENT.md",
        ROOT / "docs/planning/tasks/016_public-demo-provision-and-deploy__codex-luna-5-6__high.md",
        ROOT / "docs/planning/tasks/017_public-demo-verification__codex-luna-5-6__high.md",
        ROOT / "compose.hosted.yml",
        ROOT / "deploy/oci/deploy.sh",
    ]
    for path in paths:
        value = path.read_text()
        assert "VM.Standard.A1.Flex" not in value, path
        assert "linux/arm64" not in value, path
        assert "arm64-hosted" not in value, path
    assert "VM.Standard.E2.1.Micro" in paths[0].read_text()


def test_native_services_are_non_root_and_private_by_default() -> None:
    base = ROOT / "deploy/oci/native"
    nats = (base / "nats.conf").read_text()
    assert "127.0.0.1:4222" in nats
    assert "127.0.0.1:8222" in nats
    api = (base / "flowstead-api.service").read_text()
    assert "User=flowstead-api\n" in api
    assert "--host 127.0.0.1" in api
    assert "EnvironmentFile=/etc/flowstead/api.env" in api
    worker = (base / "flowstead-worker.service").read_text()
    assert "User=flowstead-worker\n" in worker
    assert "MemoryMax=" in worker
    assert "EnvironmentFile=/etc/flowstead/worker.env" in worker
    assert "EnvironmentFile=/etc/flowstead/nats-worker.env" in worker
    assert "Environment=NATS_URL=" not in api + worker
    assert "include ./nats-auth.conf" in nats
    proxy = (base / "Caddyfile").read_text()
    assert "http://127.0.0.1:8080" in proxy
    assert "reverse_proxy 127.0.0.1:8000" in proxy


def test_native_example_has_no_embedded_admin_password() -> None:
    native = ROOT / "deploy/oci/native"
    api = (native / "api.env.example").read_text()
    worker = (native / "worker.env.example").read_text()
    for example, role in [(api, "flowstead_api"), (worker, "flowstead_worker")]:
        assert "MIGRATION_DATABASE_URL=" not in example
        assert f"DATABASE_URL=postgresql://{role}." in example
        assert "REPLACE_WITH_SECURE_PASSWORD" in example
        assert "sslmode=verify-full" in example
        assert "sslrootcert=" in example


def test_vercel_frontend_security_headers_and_api_non_fallback() -> None:
    """Missing /api paths must not be rendered as 200 HTML SPA responses."""
    import json
    import re

    config = json.loads((ROOT / "frontend/vercel.json").read_text())
    rewrite = config["rewrites"][0]
    assert rewrite["destination"] == "/index.html"
    source = rewrite["source"]
    # Source syntax is a Vercel path match with a negative-lookahead regex.
    assert "(?!api(?:/|$))" in source
    regex = re.compile(r"^" + source + r"$")
    assert regex.fullmatch("/plants/plant-01")
    assert regex.fullmatch("/")
    assert not regex.fullmatch("/api")
    assert not regex.fullmatch("/api/v1/public/plants")

    keys = {
        header["key"].lower(): header["value"]
        for group in config["headers"]
        for header in group["headers"]
    }
    csp = keys["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    assert "https://api.flowstead.darizae.dev" in csp
    assert keys["x-frame-options"] == "DENY"
    assert keys["x-content-type-options"] == "nosniff"
    assert keys["referrer-policy"] == "no-referrer"


def test_optional_docker_base_images_are_digest_pinned() -> None:
    """Changing a hosted builder/runtime base image requires an explicit audit."""
    text = (ROOT / "backend/Dockerfile").read_text()
    assert text.count("FROM python:3.12-slim@sha256:") == 2
    assert "FROM ghcr.io/astral-sh/uv:0.9.13@sha256:" in text
    assert "FROM python:3.12-slim AS builder" not in text
    assert "\nFROM python:3.12-slim\n" not in text
