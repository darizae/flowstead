"""Bounded local HTTP policy for the single-process demo API."""

from __future__ import annotations

import ipaddress
import math
import os
import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_DEFAULT_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class SecurityConfigurationError(ValueError):
    """Raised when local HTTP security settings are invalid."""


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    requests_per_window: int
    window_seconds: int
    max_clients: int
    max_body_bytes: int
    max_target_bytes: int
    trusted_proxies: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> SecurityConfig:
        values = os.environ if environ is None else environ
        return cls(
            requests_per_window=_bounded_int(values, "FLOWSTEAD_RATE_LIMIT_REQUESTS", 600, 1, 100_000),
            window_seconds=_bounded_int(values, "FLOWSTEAD_RATE_LIMIT_WINDOW_SECONDS", 60, 1, 3_600),
            max_clients=_bounded_int(values, "FLOWSTEAD_RATE_LIMIT_MAX_CLIENTS", 4_096, 1, 100_000),
            max_body_bytes=_bounded_int(values, "FLOWSTEAD_MAX_REQUEST_BODY_BYTES", 16_384, 0, 1_048_576),
            max_target_bytes=_bounded_int(values, "FLOWSTEAD_MAX_REQUEST_TARGET_BYTES", 8_192, 256, 65_536),
            trusted_proxies=_networks(values.get("FLOWSTEAD_TRUSTED_PROXIES", "")),
            cors_origins=_origins(values.get("FLOWSTEAD_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)),
        )


class ClientRateLimiter:
    """Fixed-window-equivalent sliding limiter with a bounded client map."""

    def __init__(self, config: SecurityConfig, *, clock: Any = time.monotonic) -> None:
        self._limit = config.requests_per_window
        self._window = float(config.window_seconds)
        self._max_clients = config.max_clients
        self._clock = clock
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client: str) -> tuple[bool, int, int]:
        now = float(self._clock())
        cutoff = now - self._window
        with self._lock:
            requests = self._requests.get(client)
            if requests is None:
                self._prune_clients(cutoff)
                if len(self._requests) >= self._max_clients:
                    return False, 0, max(1, math.ceil(self._window))
                requests = deque()
                self._requests[client] = requests
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= self._limit:
                retry_after = max(1, math.ceil(self._window - (now - requests[0])))
                return False, 0, retry_after
            requests.append(now)
            return True, self._limit - len(requests), 0

    def _prune_clients(self, cutoff: float) -> None:
        expired = [client for client, requests in self._requests.items() if not requests or requests[-1] <= cutoff]
        for client in expired:
            del self._requests[client]


class HttpSecurityMiddleware:
    """Enforce request bounds, trusted-proxy identity, rate limits and response headers."""

    def __init__(self, app: ASGIApp, *, config: SecurityConfig) -> None:
        self.app = app
        self.config = config
        self.limiter = ClientRateLimiter(config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        error = _request_error(scope, self.config)
        if error is not None:
            await self._respond(scope, receive, send, error[0], error[1])
            return
        try:
            client = _client_ip(scope, self.config.trusted_proxies)
        except ValueError:
            await self._respond(scope, receive, send, 400, "Invalid forwarded client address")
            return
        allowed, remaining, retry_after = self.limiter.check(client)
        if not allowed:
            await self._respond(
                scope,
                receive,
                send,
                429,
                "Request rate limit exceeded",
                {"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
            )
            return

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                _set_security_headers(headers, scope)
                headers["X-RateLimit-Limit"] = str(self.config.requests_per_window)
                headers["X-RateLimit-Remaining"] = str(remaining)
            await send(message)

        await self.app(scope, receive, secure_send)

    async def _respond(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        message: str,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        body = {"detail": {"code": "request_denied", "message": message}}
        response = JSONResponse(body, status_code=status_code, headers=dict(headers or {}))

        async def secure_send(event: Message) -> None:
            if event["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=event)
                _set_security_headers(response_headers, scope)
                response_headers["X-RateLimit-Limit"] = str(self.config.requests_per_window)
            await send(event)

        await response(scope, receive, secure_send)


def _request_error(scope: Scope, config: SecurityConfig) -> tuple[int, str] | None:
    target_size = len(scope.get("raw_path", b"")) + len(scope.get("query_string", b""))
    if target_size > config.max_target_bytes:
        return 414, "Request target is too large"
    headers = {key.lower(): value for key, value in scope.get("headers", [])}
    if b"transfer-encoding" in headers:
        return 413, "Request body is too large"
    content_length = headers.get(b"content-length")
    if content_length is None:
        return None
    try:
        length = int(content_length)
    except ValueError:
        return 400, "Invalid Content-Length"
    if length < 0:
        return 400, "Invalid Content-Length"
    if length > config.max_body_bytes:
        return 413, "Request body is too large"
    return None


def _client_ip(
    scope: Scope,
    trusted_proxies: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
) -> str:
    peer_value = scope.get("client")
    peer_host = str(peer_value[0] if peer_value else "127.0.0.1")
    try:
        peer = ipaddress.ip_address(peer_host)
    except ValueError:
        return peer_host[:128]
    if not _trusted(peer, trusted_proxies):
        return peer.compressed
    headers = {key.lower(): value for key, value in scope.get("headers", [])}
    forwarded = headers.get(b"x-forwarded-for")
    if forwarded is None:
        return peer.compressed
    try:
        parts = forwarded.decode("ascii").split(",")
        if not 1 <= len(parts) <= 16:
            raise ValueError
        addresses = [ipaddress.ip_address(part.strip()) for part in parts]
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("invalid X-Forwarded-For") from error
    for address in reversed(addresses):
        if not _trusted(address, trusted_proxies):
            return address.compressed
    return addresses[0].compressed


def _trusted(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
) -> bool:
    return any(address.version == network.version and address in network for network in networks)


def _set_security_headers(headers: MutableHeaders, scope: Scope) -> None:
    for name, value in _SECURITY_HEADERS.items():
        if (
            name.lower() != "content-security-policy"
            or str(scope.get("path", "")).startswith("/api/")
        ) and name not in headers:
            headers[name] = value


def _bounded_int(values: Mapping[str, str], name: str, default: int, minimum: int, maximum: int) -> int:
    raw = values.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise SecurityConfigurationError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise SecurityConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _networks(raw: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    try:
        return tuple(ipaddress.ip_network(item.strip(), strict=False) for item in raw.split(",") if item.strip())
    except ValueError as error:
        raise SecurityConfigurationError("FLOWSTEAD_TRUSTED_PROXIES contains an invalid CIDR") from error


def _origins(raw: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in raw.split(","):
        origin = item.strip()
        if not origin:
            continue
        parsed = urlsplit(origin)
        is_loopback_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1", "localhost"}
        if (
            parsed.scheme not in {"https", "http"}
            or (parsed.scheme == "http" and not is_loopback_http)
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or origin == "*"
        ):
            raise SecurityConfigurationError("FLOWSTEAD_CORS_ORIGINS must contain exact HTTPS or loopback HTTP origins")
        normalized = f"{parsed.scheme}://{parsed.netloc}"
        if normalized not in result:
            result.append(normalized)
    return tuple(result)
