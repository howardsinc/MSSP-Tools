"""Local config persistence — saves the partner's last-used gateway URL.

Saved to %APPDATA%\\FortiAIGate-Onboarder\\config.json on Windows, or
~/.config/fortiaigate-onboarder/config.json on POSIX.

Admin credentials are NEVER persisted — partners enter them each session.
Only the gateway URL (non-secret) is remembered.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        return base / "FortiAIGate-Onboarder"
    return Path.home() / ".config" / "fortiaigate-onboarder"


def _config_path() -> Path:
    return _config_dir() / "config.json"


def load() -> dict:
    p = _config_path()
    if not p.exists():
        return {"gateway_url": "https://192.168.215.22:8443"}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"gateway_url": "https://192.168.215.22:8443"}


def save(data: dict) -> None:
    # Never persist secrets.
    safe = {
        "gateway_url": data.get("gateway_url", ""),
        "admin_username": data.get("admin_username", "admin"),
        "last_global_bearer_hint": data.get("last_global_bearer_hint", ""),
    }
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(safe, indent=2), encoding="utf-8")
