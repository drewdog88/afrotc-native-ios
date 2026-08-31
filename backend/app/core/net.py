"""Resolve the real client IP behind Vercel.

Vercel **overwrites** ``X-Forwarded-For`` with the true client IP and does not
forward client-supplied values, specifically to prevent IP spoofing
(https://vercel.com/docs/headers/request-headers), so a browser cannot forge it
on a direct Vercel deployment. ``x-vercel-forwarded-for`` is the canonical value
Vercel sets and — unlike ``x-forwarded-for`` — is *not* rewritten if another
proxy is ever placed on top, so we prefer it, then fall back to ``x-real-ip``,
then the first ``x-forwarded-for`` hop, then the socket peer.

Taking the first (left-most) comma hop is correct here: Vercel populates these
with a single client IP, not a client-controlled proxy chain.
"""
from __future__ import annotations

# Vercel-set headers in order of trust. All three carry the true client IP;
# x-vercel-forwarded-for survives a proxy-on-top rewrite that x-forwarded-for
# would not, so it is preferred.
_TRUSTED_IP_HEADERS = ("x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for")


def client_ip(request) -> str | None:
    """Best-effort real client IP, or ``None`` if it can't be determined."""
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers is not None:
        for name in _TRUSTED_IP_HEADERS:
            value = headers.get(name)
            if value:
                ip = value.split(",")[0].strip()
                if ip:
                    return ip
    client = getattr(request, "client", None)
    return getattr(client, "host", None)
