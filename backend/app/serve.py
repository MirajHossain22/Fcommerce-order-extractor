"""Single-process pilot server with explicit persistent storage and host checks."""

import os
from pathlib import Path

import uvicorn
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.main import create_app


def build_app():
    raw_path = os.environ.get("DATABASE_PATH", "")
    hosts = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "").split(",") if host.strip()]
    render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_host and render_host not in hosts:
        hosts.append(render_host)
    if not raw_path or not Path(raw_path).is_absolute():
        raise ValueError("DATABASE_PATH must be an absolute path on persistent storage")
    if not Path(raw_path).parent.is_dir():
        raise ValueError("DATABASE_PATH parent directory must already exist")
    if not hosts or any("*" in host or "/" in host or ":" in host for host in hosts):
        raise ValueError("Set ALLOWED_HOSTS or RENDER_EXTERNAL_HOSTNAME to explicit hostnames without schemes or ports")
    # Production startup must not silently leave the seller application unusable.
    import json
    keys = json.loads(os.environ.get("SELLER_API_KEYS") or "{}")
    if not isinstance(keys, dict) or not keys or any(not isinstance(key, str) or len(key) < 32 for key in keys):
        raise ValueError("Set SELLER_API_KEYS with at least one random key of 32 or more characters")
    application = create_app(Path(raw_path), seller_keys=keys)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts, www_redirect=False)
    return application


def main() -> None:
    uvicorn.run(build_app(), host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")),
                workers=1, access_log=False, proxy_headers=True,
                forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"))


if __name__ == "__main__":
    main()
