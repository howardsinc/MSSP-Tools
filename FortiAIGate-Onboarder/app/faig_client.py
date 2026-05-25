"""Async FortiAIGate admin API client.

Ports `api/examples/05-onboard-tenant.sh` to Python + httpx. The gateway uses:
  - cookie session (set by POST /api/login)
  - CSRF token (returned by /api/login, must be sent as X-CSRF-Token header)
  - self-signed TLS (we verify=False — the appliance ships a self-signed cert
    and partners typically run this tool on a private LAN to the gateway)

Source: api/reference/01-auth.md + the verified lab build.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from .providers import needs_private_endpoint
from .scanners import build_input_guard, build_output_guard


class FaigError(Exception):
    pass


class FaigClient:
    """One client = one admin session. Re-instantiate per gateway/admin."""

    def __init__(self, base_url: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._csrf: str | None = None
        # verify=False: appliance cert is self-signed; this tool runs on
        # the partner's machine pointed at their gateway over private LAN.
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            verify=False,
            timeout=timeout,
            headers={"Host": "fortiaigate.local"},
        )

    async def close(self):
        await self._client.aclose()

    # ------------------------------------------------------------------ auth

    async def login(self, username: str, password: str) -> dict:
        r = await self._client.post(
            "/api/login",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
        )
        try:
            body = r.json()
        except Exception:
            raise FaigError(f"Login returned non-JSON (HTTP {r.status_code}): {r.text[:200]}")
        if body.get("message") != "Login successful":
            raise FaigError(f"Login failed: {body}")
        self._csrf = body.get("csrf_token")
        if not self._csrf:
            raise FaigError("Login OK but no csrf_token in response")
        return {"username": username, "csrf_token_captured": True}

    def _headers(self, has_body: bool = False) -> dict:
        h: dict[str, str] = {}
        if has_body:
            h["Content-Type"] = "application/json"
        if self._csrf:
            h["X-CSRF-Token"] = self._csrf
        return h

    # ----------------------------------------------------------------- flows

    async def list_flows(self) -> list[dict]:
        r = await self._client.get("/api/ai-flow", headers=self._headers())
        r.raise_for_status()
        body = r.json()
        return body.get("items") if isinstance(body, dict) and "items" in body else body

    async def get_flow(self, uuid: str) -> dict:
        r = await self._client.get(f"/api/ai-flow/{uuid}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def create_flow(self, name: str, path: str, guard_uuid: str) -> dict:
        body = {
            "name": name,
            "path": path,
            "schema": ["openai/v1/chat/completions"],
            "routingType": "single",
            "guards": [{"uuid": guard_uuid, "routingName": None, "selectors": None}],
            "webCache": {"enabled": False, "inactiveAfter": 0, "unit": "seconds"},
            "rateLimit": {"enabled": False, "requestsThreshold": 0, "interval": 0, "unit": "seconds"},
            "authentication": {"enabled": True, "customHeader": ""},
        }
        r = await self._client.post("/api/ai-flow", json=body, headers=self._headers(has_body=True))
        if r.status_code >= 400:
            raise FaigError(f"Flow create failed (HTTP {r.status_code}): {r.text[:400]}")
        resp = r.json()
        if "uuid" not in resp:
            raise FaigError(f"Flow create returned no uuid: {resp}")
        return resp

    async def delete_flow(self, uuid: str) -> None:
        r = await self._client.delete(f"/api/ai-flow/{uuid}", headers=self._headers())
        if r.status_code >= 400 and r.status_code != 404:
            raise FaigError(f"Flow delete failed (HTTP {r.status_code}): {r.text[:200]}")

    # ---------------------------------------------------------------- guards

    async def list_guards(self) -> list[dict]:
        r = await self._client.get("/api/ai-guard", headers=self._headers())
        r.raise_for_status()
        body = r.json()
        return body.get("items") if isinstance(body, dict) and "items" in body else body

    async def get_guard(self, uuid: str) -> dict:
        r = await self._client.get(f"/api/ai-guard/{uuid}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def create_guard(self, name: str, *, policy: str,
                           custom_scanners: dict | None,
                           provider_id: str,
                           model: str, executor: str, endpoint: str,
                           apikey: str | None = None,
                           aws: dict | None = None) -> dict:
        priv = needs_private_endpoint(provider_id, endpoint)
        service: dict[str, Any] = {
            "type": model,
            "executor": executor,
            "endpoint": endpoint,
            "apikey": apikey or "",
            "url": None,
            "accessKeyId": (aws or {}).get("access_key_id"),
            "secretAccessKey": (aws or {}).get("secret_access_key"),
            "regionName": (aws or {}).get("region"),
            "privateEndpointEnabled": priv,
            "tokenPricingEnabled": True,
            "inputCost": 0.2,
            "outputCost": 0.2,
            "selectors": None,
            "params": {"enable": False},
        }
        body = {
            "name": name,
            "inputGuard": build_input_guard(policy, custom_scanners),
            "inputGuardAdvanced": False,
            "outputGuard": build_output_guard(policy, custom_scanners),
            "outputGuardAdvanced": False,
            "aiProvider": [service],
        }
        r = await self._client.post("/api/ai-guard", json=body, headers=self._headers(has_body=True))
        if r.status_code >= 400:
            raise FaigError(f"Guard create failed (HTTP {r.status_code}): {r.text[:400]}")
        resp = r.json()
        if "uuid" not in resp:
            raise FaigError(f"Guard create returned no uuid: {resp}")
        return resp

    async def delete_guard(self, uuid: str) -> None:
        r = await self._client.delete(f"/api/ai-guard/{uuid}", headers=self._headers())
        if r.status_code >= 400 and r.status_code != 404:
            raise FaigError(f"Guard delete failed (HTTP {r.status_code}): {r.text[:200]}")

    # ----------------------------------------------------------- idempotency

    async def find_flow_uuid(self, name: str) -> str | None:
        for f in await self.list_flows():
            if f.get("name") == name:
                return f.get("uuid")
        return None

    async def find_guard_uuid(self, name: str) -> str | None:
        for g in await self.list_guards():
            if g.get("name") == name:
                return g.get("uuid")
        return None

    # -------------------------------------------------------- data-plane test

    async def smoke_test(self, path: str, bearer: str, *, model: str, prompt: str,
                         max_tokens: int = 25, timeout: float = 60.0) -> dict:
        """Send one /v1/.../chat/completions and report HTTP code + latency + content + scanner verdict."""
        t0 = time.monotonic()
        try:
            r = await self._client.post(
                path,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                },
                headers={
                    "Authorization": f"Bearer {bearer}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
            elapsed = time.monotonic() - t0
            try:
                body = r.json()
            except Exception:
                body = {"raw_text": r.text[:500]}
            verdict = "passed"
            content = ""
            try:
                choice = body.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                finish = choice.get("finish_reason", "")
                blocked_id = body.get("id", "")
                if finish == "content_filter" or blocked_id == "chatcmpl-blocked":
                    verdict = "blocked"
            except Exception:
                pass
            if r.status_code >= 500:
                verdict = "error"
            elif r.status_code >= 400:
                verdict = "auth-error"
            return {
                "http_code": r.status_code,
                "elapsed_s": round(elapsed, 3),
                "verdict": verdict,
                "content": content,
                "body": body,
            }
        except httpx.RequestError as e:
            return {
                "http_code": 0,
                "elapsed_s": round(time.monotonic() - t0, 3),
                "verdict": "network-error",
                "content": "",
                "body": {"error": str(e)},
            }
