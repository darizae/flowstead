"""SEC19-04: migration-owner credentials must never reach runtime Compose."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_hosted_runtime_example_excludes_migration_owner_credentials() -> None:
    runtime = (REPO_ROOT / "deploy/oci/env.hosted.example").read_text()
    migration = (REPO_ROOT / "deploy/oci/env.migration.example").read_text()
    non_comment_lines = "\n".join(
        line for line in runtime.splitlines() if not line.lstrip().startswith("#")
    )
    assert re.search(r"(?m)^DATABASE_URL=", non_comment_lines)
    assert not re.search(r"(?m)^MIGRATION_DATABASE_URL=", non_comment_lines)
    assert re.search(r"(?m)^MIGRATION_DATABASE_URL=", migration)


def test_deployment_fails_closed_if_migration_secret_would_reach_containers() -> None:
    script = (REPO_ROOT / "deploy/oci/deploy.sh").read_text()
    assert "MIGRATION_DATABASE_URL" in script
    assert "grep -Eq" in script
    assert script.index("grep -Eq") < script.index("docker build")
    compose = (REPO_ROOT / "compose.hosted.yml").read_text()
    assert "HOSTED_ENV_FILE" in compose
    assert "MIGRATION_DATABASE_URL" not in compose
