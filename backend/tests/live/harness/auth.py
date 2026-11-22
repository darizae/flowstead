"""Local HTTPS JWKS authority issuing genuine RS256 test tokens."""

from __future__ import annotations

import base64
import datetime as dt
import http.server
import ipaddress
import json
import ssl
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

AUDIENCE = "authenticated"
KEY_ID = "flowstead-live-rs256"


def _b64_uint(value: int) -> str:
    size = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


def _certificate_pair() -> tuple[
    rsa.RSAPrivateKey, x509.Certificate, rsa.RSAPrivateKey, x509.Certificate
]:
    """Create a short-lived CA and a localhost certificate signed by it."""
    now = dt.datetime.now(dt.UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Flowstead live test CA")])
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(hours=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    server_certificate = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_certificate.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(hours=2))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return ca_key, ca_certificate, server_key, server_certificate


class _ThreadingHttpsServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


@dataclass
class LocalJwksAuthority:
    """A real local HTTPS JWKS endpoint and its private signing key."""

    issuer: str
    private_key: rsa.RSAPrivateKey
    ca_path: Path
    _server: _ThreadingHttpsServer
    _thread: threading.Thread
    _temporary_directory: tempfile.TemporaryDirectory[str]

    @classmethod
    def start(cls) -> LocalJwksAuthority:
        _ca_key, ca_certificate, server_key, server_certificate = _certificate_pair()
        temporary_directory = tempfile.TemporaryDirectory(prefix="flowstead-live-jwks-")
        directory = Path(temporary_directory.name)
        ca_path = directory / "ca.pem"
        key_path = directory / "server-key.pem"
        certificate_path = directory / "server-cert.pem"
        ca_path.write_bytes(ca_certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            server_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        certificate_path.write_bytes(server_certificate.public_bytes(serialization.Encoding.PEM))

        public_numbers = server_key.public_key().public_numbers()
        jwks = json.dumps(
            {
                "keys": [
                    {
                        "kty": "RSA",
                        "kid": KEY_ID,
                        "alg": "RS256",
                        "use": "sig",
                        "n": _b64_uint(public_numbers.n),
                        "e": _b64_uint(public_numbers.e),
                    }
                ]
            }
        ).encode()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/.well-known/jwks.json":
                    self.send_error(http.HTTPStatus.NOT_FOUND)
                    return
                self.send_response(http.HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(jwks)))
                self.end_headers()
                self.wfile.write(jwks)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        try:
            server = _ThreadingHttpsServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=certificate_path, keyfile=key_path)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(
                target=server.serve_forever, name="flowstead-live-jwks", daemon=True
            )
            thread.start()
        except BaseException:
            temporary_directory.cleanup()
            raise
        port = int(server.server_address[1])
        return cls(
            issuer=f"https://127.0.0.1:{port}",
            private_key=server_key,
            ca_path=ca_path,
            _server=server,
            _thread=thread,
            _temporary_directory=temporary_directory,
        )

    def environment(self) -> dict[str, str]:
        return {
            "FLOWSTEAD_AUTH_MODE": "supabase",
            "SUPABASE_AUTH_URL": self.issuer,
            "SUPABASE_JWT_ISSUER": self.issuer,
            "SUPABASE_JWT_AUDIENCE": AUDIENCE,
            "SUPABASE_JWT_ALGORITHMS": "RS256",
            "SUPABASE_AUTH_VERIFICATION_MODE": "jwks",
            "SSL_CERT_FILE": str(self.ca_path),
        }

    def token(self, subject: str, *, minutes: int = 10) -> str:
        now = dt.datetime.now(dt.UTC)
        claims: dict[str, Any] = {
            "sub": subject,
            "iss": self.issuer,
            "aud": AUDIENCE,
            "iat": int((now - dt.timedelta(seconds=1)).timestamp()),
            "nbf": int((now - dt.timedelta(seconds=1)).timestamp()),
            "exp": int((now + dt.timedelta(minutes=minutes)).timestamp()),
        }
        return jwt.encode(
            claims,
            self.private_key,
            algorithm="RS256",
            headers={"kid": KEY_ID, "typ": "JWT"},
        )

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._temporary_directory.cleanup()


__all__ = ["AUDIENCE", "KEY_ID", "LocalJwksAuthority"]
