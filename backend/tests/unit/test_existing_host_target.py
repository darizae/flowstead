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
    assert "User=flowstead" in api
    assert "--host 127.0.0.1" in api
    assert "EnvironmentFile=/etc/flowstead/runtime.env" in api
    worker = (base / "flowstead-worker.service").read_text()
    assert "User=flowstead" in worker
    assert "MemoryMax=" in worker
    proxy = (base / "Caddyfile").read_text()
    assert "http://127.0.0.1:8080" in proxy
    assert "reverse_proxy 127.0.0.1:8000" in proxy


def test_native_example_has_no_embedded_admin_password() -> None:
    example = (ROOT / "deploy/oci/native/runtime.env.example").read_text()
    assert "MIGRATION_DATABASE_URL=" not in example
    assert "REPLACE_WITH_SECRET" in example
    assert "sslmode=verify-full" in example
