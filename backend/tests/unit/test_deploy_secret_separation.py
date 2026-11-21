"""SEC19-04: separately scoped database passwords must not cross runtime services."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_native_api_and_worker_use_different_files() -> None:
    native = ROOT / "deploy/oci/native"
    api = (native / "flowstead-api.service").read_text()
    worker = (native / "flowstead-worker.service").read_text()
    assert "EnvironmentFile=/etc/flowstead/api.env" in api
    assert "EnvironmentFile=/etc/flowstead/worker.env" in worker
    assert "EnvironmentFile=/etc/flowstead/runtime.env" not in api + worker
    assert "MIGRATION_DATABASE_URL" not in api + worker


def test_hosted_compose_separates_api_and_worker_credentials() -> None:
    compose = (ROOT / "compose.hosted.yml").read_text()
    assert "HOSTED_API_ENV_FILE" in compose
    assert "HOSTED_WORKER_ENV_FILE" in compose
    assert "HOSTED_ENV_FILE" not in compose
    assert "MIGRATION_DATABASE_URL" not in compose
    assert "HOSTED_NATS_AUTH_FILE" in compose
    assert "nats_auth:" in compose
    assert "nats-auth.conf" in compose
    assert "NATS_URL: nats://nats:4222" not in compose
    base = compose.split("x-backend: &backend", 1)[1].split("services:", 1)[0]
    assert "env_file:" not in base

    api = (ROOT / "deploy/oci/env.api.example").read_text()
    worker = (ROOT / "deploy/oci/env.worker.example").read_text()
    assert "DATABASE_URL=postgresql://flowstead_api." in api
    assert "DATABASE_URL=postgresql://flowstead_worker." in worker
    assert "sslmode=verify-full" in api and "sslrootcert=" in api
    assert "sslmode=verify-full" in worker and "sslrootcert=" in worker
    assert "NATS_URL=nats://REPLACE_WITH_SEPARATE_BROKER_TOKEN@nats:4222" in worker
    assert "MIGRATION_DATABASE_URL" not in api + worker
    assert "SUPABASE_SERVICE_ROLE_KEY=" not in api + worker


def test_deployment_rejects_privileged_or_swapped_credentials() -> None:
    script = (ROOT / "deploy/oci/deploy.sh").read_text()
    assert "MIGRATION_DATABASE_URL" in script
    assert "SUPABASE_SERVICE_ROLE_KEY" in script
    assert "realpath" in script
    assert "wrong database role" in script
    assert "verified TLS with explicit CA" in script
    assert "NATS worker token mismatch" in script
    assert script.index("check_secret_file") < script.index("docker build")


def test_supabase_role_migration_grants_no_immutable_data_writes() -> None:
    script = (ROOT / "deploy/supabase/005_least_privilege_runtime_roles.sql").read_text()
    assert "ALTER ROLE flowstead_runtime NOLOGIN" in script
    assert "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA app" in script
    assert "CREATE ROLE flowstead_api NOLOGIN" in script
    assert "CREATE ROLE flowstead_worker NOLOGIN" in script
    assert "app.operator_plant_access" in script
    assert "GRANT UPDATE ON TABLE" in script
    write_section = script.split("GRANT UPDATE ON TABLE", 1)[1].split("TO flowstead_worker", 1)[0]
    assert "operator_plant_access" not in write_section
    assert "hourly_readings" not in write_section
    assert "ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY" in script
