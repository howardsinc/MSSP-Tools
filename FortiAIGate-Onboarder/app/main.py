"""FortiAIGate Onboarder — FastAPI backend.

Serves the single-page wizard + dashboard at http://localhost:8765/ and
exposes a thin JSON API that wraps `app.faig_client.FaigClient`.

The session model is intentionally simple: when the partner POSTs
/api/connect with their admin creds, we hold one `FaigClient` instance in
process memory keyed by a session UUID. No secrets touch disk. If the
process restarts, the partner re-enters creds. This is acceptable for a
single-user tool that lives on the partner's laptop.
"""

from __future__ import annotations

import secrets
import threading
import urllib.parse
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Cookie, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config as cfg
from .faig_client import FaigClient, FaigError
from .providers import PROVIDERS
from .scanners import SCANNER_INFO


SESSIONS: dict[str, FaigClient] = {}
SESSION_GATEWAY: dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for client in list(SESSIONS.values()):
        try:
            await client.close()
        except Exception:
            pass


app = FastAPI(title="FortiAIGate Onboarder", version="0.1.0", lifespan=lifespan)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============================================================ models


class ConnectReq(BaseModel):
    gateway_url: str
    username: str = "admin"
    password: str


class ScannerCustom(BaseModel):
    action_pi: str = "alert"
    action_dlp: str = "alert"
    action_tox: str = "alert"
    enabled: dict[str, bool] = Field(default_factory=dict)


class CreateTenantReq(BaseModel):
    customer_name: str = Field(..., description="Slug-style, e.g. 'customer-1-acme'")
    path_prefix: str = Field(..., description="Path segment, e.g. 'customer1' (no slash)")
    secret_token: str = Field(..., description="16+ char unguessable token")
    provider_id: str = Field(..., description="Key from PROVIDERS")
    model: str
    endpoint: str = ""
    upstream_key: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str | None = None
    policy: str = "alert"  # alert | strict-block | custom
    custom: ScannerCustom | None = None


class SmokeTestReq(BaseModel):
    path: str
    bearer: str
    model: str
    prompt: str = "Reply: SMOKE_OK"
    max_tokens: int = 25


class ConfigSaveReq(BaseModel):
    gateway_url: str
    admin_username: str = "admin"


# ============================================================ helpers


def _client_for(session_id: str | None) -> FaigClient:
    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not connected. POST /api/connect first.")
    return SESSIONS[session_id]


def _gateway_for(session_id: str | None) -> str:
    if not session_id or session_id not in SESSION_GATEWAY:
        raise HTTPException(status_code=401, detail="Not connected.")
    return SESSION_GATEWAY[session_id]


# ============================================================ routes — meta


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/providers")
async def list_providers():
    return {"providers": PROVIDERS}


@app.get("/api/scanners")
async def list_scanners():
    return {"scanners": SCANNER_INFO}


@app.get("/api/config")
async def get_config():
    return cfg.load()


@app.post("/api/config")
async def save_config(req: ConfigSaveReq):
    cfg.save(req.model_dump())
    return {"saved": True}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ============================================================ routes — auth


@app.post("/api/connect")
async def connect(req: ConnectReq, response: Response):
    client = FaigClient(req.gateway_url)
    try:
        info = await client.login(req.username, req.password)
    except FaigError as e:
        await client.close()
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        await client.close()
        raise HTTPException(status_code=502, detail=f"Cannot reach gateway: {e}")

    session_id = secrets.token_urlsafe(24)
    SESSIONS[session_id] = client
    SESSION_GATEWAY[session_id] = req.gateway_url

    # Save gateway URL (NOT password) so next run pre-fills the form
    cfg.save({"gateway_url": req.gateway_url, "admin_username": req.username})

    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return {"connected": True, "gateway_url": req.gateway_url, **info}


@app.post("/api/disconnect")
async def disconnect(response: Response, session_id: str | None = Cookie(default=None)):
    if session_id and session_id in SESSIONS:
        try:
            await SESSIONS[session_id].close()
        except Exception:
            pass
        SESSIONS.pop(session_id, None)
        SESSION_GATEWAY.pop(session_id, None)
    response.delete_cookie("session_id")
    return {"disconnected": True}


@app.get("/api/connection")
async def connection_status(session_id: str | None = Cookie(default=None)):
    if session_id and session_id in SESSIONS:
        return {"connected": True, "gateway_url": SESSION_GATEWAY.get(session_id, "")}
    return {"connected": False, "gateway_url": ""}


# ============================================================ routes — tenants


@app.get("/api/tenants")
async def list_tenants(session_id: str | None = Cookie(default=None)):
    """List every Flow + match its first Guard (the tenant view).

    A 'tenant' here = one Flow whose path starts with /v1/<prefix>/<token>/
    plus the Guard it points at. Pure read; no mutation.
    """
    client = _client_for(session_id)
    try:
        flows = await client.list_flows()
        guards = await client.list_guards()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    guard_by_uuid = {g.get("uuid"): g for g in (guards or [])}
    tenants = []
    for f in flows or []:
        path = f.get("path", "")
        # parse /v1/<prefix>/<secret>/chat/completions
        parts = path.strip("/").split("/")
        prefix, secret = "", ""
        if len(parts) >= 4 and parts[0] == "v1":
            prefix = parts[1]
            secret = parts[2]
        guard_uuid_ref = (f.get("guards") or [{}])[0].get("uuid")
        g = guard_by_uuid.get(guard_uuid_ref) or {}
        provider_list = g.get("aiProvider") or [{}]
        prov = provider_list[0] if provider_list else {}
        tenants.append({
            "flow_uuid": f.get("uuid"),
            "guard_uuid": g.get("uuid"),
            "flow_name": f.get("name"),
            "guard_name": g.get("name"),
            "path": path,
            "path_prefix": prefix,
            "secret_token": secret,
            "executor": prov.get("executor"),
            "model": prov.get("type"),
            "endpoint": prov.get("endpoint"),
            "private_endpoint": prov.get("privateEndpointEnabled"),
            "auth_enabled": (f.get("authentication") or {}).get("enabled", False),
        })
    return {"tenants": tenants}


@app.get("/api/tenants/{flow_uuid}")
async def get_tenant_detail(flow_uuid: str, session_id: str | None = Cookie(default=None)):
    client = _client_for(session_id)
    flow = await client.get_flow(flow_uuid)
    guard_uuid = (flow.get("guards") or [{}])[0].get("uuid")
    guard = await client.get_guard(guard_uuid) if guard_uuid else None
    return {"flow": flow, "guard": guard}


@app.post("/api/tenants")
async def create_tenant(req: CreateTenantReq, session_id: str | None = Cookie(default=None)):
    client = _client_for(session_id)
    gateway = _gateway_for(session_id)

    provider = PROVIDERS.get(req.provider_id)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Unknown provider_id: {req.provider_id}")

    endpoint = req.endpoint or provider.get("endpoint", "")
    if not endpoint:
        raise HTTPException(status_code=400, detail="endpoint required for this provider")

    guard_name = f"{req.customer_name}-guard"
    flow_name = f"{req.customer_name}-flow"
    tenant_path = f"/v1/{req.path_prefix.strip('/')}/{req.secret_token}/chat/completions"

    # Idempotency: clean existing
    try:
        existing_flow = await client.find_flow_uuid(flow_name)
        if existing_flow:
            await client.delete_flow(existing_flow)
        existing_guard = await client.find_guard_uuid(guard_name)
        if existing_guard:
            await client.delete_guard(existing_guard)
    except FaigError as e:
        raise HTTPException(status_code=502, detail=f"Cleanup failed: {e}")

    aws = None
    if req.aws_access_key_id and req.aws_secret_access_key:
        aws = {
            "access_key_id": req.aws_access_key_id,
            "secret_access_key": req.aws_secret_access_key,
            "region": req.aws_region or "us-east-1",
        }

    custom = req.custom.model_dump() if req.custom else None

    try:
        guard = await client.create_guard(
            guard_name,
            policy=req.policy,
            custom_scanners=custom,
            provider_id=req.provider_id,
            model=req.model,
            executor=provider["executor"],
            endpoint=endpoint,
            apikey=req.upstream_key,
            aws=aws,
        )
        flow = await client.create_flow(flow_name, tenant_path, guard["uuid"])
    except FaigError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "created": True,
        "tenant": {
            "customer_name": req.customer_name,
            "guard_uuid": guard["uuid"],
            "flow_uuid": flow["uuid"],
            "path": tenant_path,
            "url": f"{gateway}{tenant_path}",
            "policy": req.policy,
            "executor": provider["executor"],
            "model": req.model,
        },
    }


@app.delete("/api/tenants/{flow_uuid}")
async def delete_tenant(flow_uuid: str, session_id: str | None = Cookie(default=None)):
    client = _client_for(session_id)
    flow = await client.get_flow(flow_uuid)
    guard_uuid = (flow.get("guards") or [{}])[0].get("uuid")
    try:
        await client.delete_flow(flow_uuid)
        if guard_uuid:
            await client.delete_guard(guard_uuid)
    except FaigError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"deleted": True}


@app.post("/api/tenants/{flow_uuid}/smoke-test")
async def smoke_test_tenant(flow_uuid: str, req: SmokeTestReq,
                            session_id: str | None = Cookie(default=None)):
    client = _client_for(session_id)
    # use the gateway-bound client to hit the data plane through the same TLS path
    result = await client.smoke_test(
        req.path, req.bearer, model=req.model, prompt=req.prompt, max_tokens=req.max_tokens,
    )
    return result


# ============================================================ helpers — frontend nav


@app.get("/wizard")
async def wizard_redirect():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard")
async def dashboard_redirect():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/settings")
async def settings_redirect():
    return FileResponse(STATIC_DIR / "index.html")


# ============================================================ launcher


def _open_browser_when_ready(port: int):
    """Open the default browser ~1.5s after server start (gives uvicorn time to bind)."""
    import time
    time.sleep(1.5)
    try:
        webbrowser.open(f"http://localhost:{port}/")
    except Exception:
        pass


def main():
    import uvicorn

    port = 8765
    host = "127.0.0.1"

    threading.Thread(target=_open_browser_when_ready, args=(port,), daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="warning",
        reload=False,
    )


if __name__ == "__main__":
    main()
