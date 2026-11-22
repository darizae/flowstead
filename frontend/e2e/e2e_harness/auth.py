"""Throwaway Supabase-compatible RS256 JWT authority for the browser gate."""

from __future__ import annotations

import base64
import datetime
import http.server
import ipaddress
import json
import ssl
import tempfile
import threading
from pathlib import Path

import certifi
import jwt
import psycopg
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .proc import RunnerError

TEST_AUTH_PORT = 8443
TEST_AUTH_BASE = f"https://127.0.0.1:{TEST_AUTH_PORT}/auth/v1"
TEST_AUTH_ISSUER = TEST_AUTH_BASE
TEST_AUTH_AUDIENCE = "authenticated"
TEST_AUTH_KEY_ID = "e2e-test-key"


def seed_principal_access(database_url: str, assignments: dict[str, list[str]]) -> None:
    """Grant the deterministic test principals access to M1 Plants in the DB."""
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        for subject, plant_ids in assignments.items():
            for plant_id in plant_ids:
                cursor.execute(
                    "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (subject, plant_id),
                )


def _generate_ca() -> tuple[
    rsa.RSAPrivateKey, x509.Certificate, rsa.RSAPrivateKey, x509.Certificate
]:
    """Return (ca_key, ca_cert, server_key, server_cert)."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Flowstead E2E Test CA")]
    )
    now = datetime.datetime.now(datetime.UTC)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return ca_key, ca_cert, server_key, server_cert


class _JWKSHandler(http.server.BaseHTTPRequestHandler):
    """Serve the test authority JWKS document over HTTPS for FastAPI verification."""

    jwks_document = b""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.jwks_document)

    def log_message(self, _format: str, *args: object) -> None:
        return


def _start_jwks_server(
    server_key: rsa.RSAPrivateKey, server_cert: x509.Certificate
) -> http.server.HTTPServer:
    """Start an HTTPS mock Auth authority resolving /.well-known/jwks.json."""
    public_numbers = server_key.public_key().public_numbers()

    def _b64(value: int) -> str:
        length = (value.bit_length() + 7) // 8
        return (
            base64.urlsafe_b64encode(value.to_bytes(length, "big"))
            .rstrip(b"=")
            .decode()
        )

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": TEST_AUTH_KEY_ID,
                "alg": "RS256",
                "use": "sig",
                "n": _b64(public_numbers.n),
                "e": _b64(public_numbers.e),
            }
        ]
    }
    _JWKSHandler.jwks_document = json.dumps(jwks).encode()
    server = http.server.HTTPServer(("127.0.0.1", TEST_AUTH_PORT), _JWKSHandler)

    def _pem(data: bytes) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as path:
            path.write(data)
            return path.name

    key_path = _pem(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    cert_path = _pem(server_cert.public_bytes(serialization.Encoding.PEM))
    server.flowstead_temp_files = [key_path, cert_path]
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(keyfile=key_path, certfile=cert_path)
    except BaseException:
        server.server_close()
        for path in (key_path, cert_path):
            Path(path).unlink(missing_ok=True)
        raise
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def mint_token(
    private_key: rsa.RSAPrivateKey, subject: str, *, minutes: int = 30
) -> str:
    now = datetime.datetime.now(datetime.UTC)
    claims = {
        "sub": subject,
        "iss": TEST_AUTH_ISSUER,
        "aud": TEST_AUTH_AUDIENCE,
        "iat": int((now - datetime.timedelta(seconds=1)).timestamp()),
        "nbf": int((now - datetime.timedelta(seconds=1)).timestamp()),
        "exp": int((now + datetime.timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": TEST_AUTH_KEY_ID, "typ": "JWT"},
    )


def setup_test_auth(env: dict[str, str], database_url: str) -> dict[str, object]:
    """Configure FastAPI to verify deterministic RS256 JWTs against a local mock authority."""
    _ca_key, ca_cert, server_key, server_cert = _generate_ca()
    # Seed two disjoint test principals against the approved M1 Plants.
    assignments = {
        "test-principal-a": ["plant-01", "plant-02"],
        "test-principal-b": ["plant-03"],
    }
    seed_principal_access(database_url, assignments)
    server = _start_jwks_server(server_key, server_cert)
    # Trust our CA alongside the system bundle so httpx (FastAPI verifier) accepts the mock.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as combined:
        combined.write(Path(certifi.where()).read_bytes())
        combined.write(b"\n")
        combined.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    server.flowstead_temp_files.append(combined.name)
    env["SUPABASE_AUTH_URL"] = TEST_AUTH_BASE
    env["SUPABASE_JWT_ISSUER"] = TEST_AUTH_ISSUER
    env["SUPABASE_JWT_AUDIENCE"] = TEST_AUTH_AUDIENCE
    env["SUPABASE_JWT_ALGORITHMS"] = "RS256"
    env["SUPABASE_AUTH_VERIFICATION_MODE"] = "jwks"
    env["SSL_CERT_FILE"] = combined.name
    env["REQUESTS_CA_BUNDLE"] = combined.name
    return {
        "server": server,
        "private_key": server_key,
        "assignments": assignments,
    }


def terminate_server(server: http.server.HTTPServer | None) -> None:
    if server is None:
        return
    try:
        server.shutdown()
        server.server_close()
    except OSError:
        pass
    finally:
        for path in getattr(server, "flowstead_temp_files", []):
            Path(path).unlink(missing_ok=True)


__all__ = [
    "TEST_AUTH_AUDIENCE",
    "TEST_AUTH_BASE",
    "TEST_AUTH_ISSUER",
    "TEST_AUTH_KEY_ID",
    "TEST_AUTH_PORT",
    "RunnerError",
    "mint_token",
    "seed_principal_access",
    "setup_test_auth",
    "terminate_server",
]
