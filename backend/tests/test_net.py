"""Client-IP resolution behind Vercel (app/core/net.py)."""
from types import SimpleNamespace

from app.core.net import client_ip


def _req(headers: dict | None = None, peer: str | None = None):
    client = SimpleNamespace(host=peer) if peer is not None else None
    return SimpleNamespace(headers=(headers or {}), client=client)


def test_none_request_is_none() -> None:
    assert client_ip(None) is None


def test_prefers_vercel_forwarded_over_xff() -> None:
    # Vercel's canonical header wins even if a spoofed x-forwarded-for is present.
    req = _req({
        "x-vercel-forwarded-for": "203.0.113.7",
        "x-real-ip": "198.51.100.9",
        "x-forwarded-for": "1.2.3.4",
    })
    assert client_ip(req) == "203.0.113.7"


def test_falls_back_to_real_ip_then_xff() -> None:
    assert client_ip(_req({"x-real-ip": "198.51.100.9"})) == "198.51.100.9"
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4"})) == "1.2.3.4"


def test_takes_first_hop_of_xff() -> None:
    assert client_ip(_req({"x-forwarded-for": "9.9.9.9, 10.0.0.1"})) == "9.9.9.9"


def test_ignores_empty_header_values() -> None:
    req = _req({"x-vercel-forwarded-for": "  ", "x-real-ip": "198.51.100.9"})
    assert client_ip(req) == "198.51.100.9"


def test_falls_back_to_socket_peer() -> None:
    assert client_ip(_req({}, peer="127.0.0.1")) == "127.0.0.1"
    assert client_ip(_req({})) is None
