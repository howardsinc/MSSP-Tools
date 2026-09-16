# FortiAIGate Onboarder

Partner-facing wizard + tenants dashboard for **FortiAIGate 8.0+**. Runs as a
local Windows app — `git clone`, double-click `start.bat`, browser opens to
the wizard.

> Built to standardise multi-tenant MSSP onboarding against the FortiAIGate
> admin API. Replaces hand-curated curl scripts with a 4-step UI that any
> partner can drive without learning the underlying REST schema.

---

## What it does

| Tab | Purpose |
|---|---|
| **+ Onboard New** | 4-step wizard: customer name + path + token → upstream LLM (Anthropic / OpenAI / Azure / Bedrock / Vertex / Zhipu / custom) → protection profile (Alert / Strict-Block / Custom) → review & create. Built-in smoke test on success. |
| **Tenants** | Live dashboard of every Flow + Guard on the gateway. Per-tenant delete + run-smoke-test against benign / prompt-injection / PII probes. |
| **Settings** | Persist default gateway URL + admin username (passwords are never saved). |

---

## Quick start

### Prerequisites
- Windows 10/11
- Network reach to a FortiAIGate gateway (any 8.0+ build)
- A FortiAIGate admin password

The launcher will install everything else (uv → Python 3.11+ → deps) on first run.

### Run
```cmd
git clone https://github.com/howardsinc/MSSP-Tools.git
cd MSSP-Tools\FortiAIGate-Onboarder
start.bat
```

If you already have MSSP-Tools cloned, just `cd FortiAIGate-Onboarder && start.bat`.

First run takes ~15s (downloads uv + Python + deps). Subsequent runs <2s.

The browser will auto-open to `http://localhost:8765/`. Enter your gateway URL
+ admin creds and start onboarding.

PowerShell users can run `.\start.ps1` instead.

---

## Wizard flow

1. **Customer Details** — Customer slug, path prefix (auto-suggested),
   16-hex secret token (auto-generated, regen button). Shows the final URL
   as you type.
2. **Upstream LLM** — Pick provider card → pick model → paste API key.
   Auto-detects when `privateEndpointEnabled=true` must be set (e.g. Zhipu
   GLM, custom OpenAI-compat endpoints). AWS Bedrock takes access key +
   secret + region instead of a single key.
3. **Protection Profile** — Three preset cards:
   - **Trust + Alert** — all 8 inbound scanners run, log only, traffic passes
     through. Use for monitoring / pilots.
   - **Strict Block** — Prompt Injection + DLP set to `alert&deny`, others
     stay alert. Use for HIPAA / PCI / regulated.
   - **Custom** — per-scanner toggle + per-scanner action override.
4. **Review & Confirm** — Read-only summary + collapsible "View JSON that
   will be POSTed" panel. One click creates Guard then Flow on the gateway.
5. **Success card** — Shows tenant URL + Bearer hint + Guard/Flow UUIDs.
   Built-in benign / injection / PII probes. Download `.env`. Copy curl.
   Pre-filled mailto for customer handoff.

---

## Tenants dashboard

Lists every Flow on the gateway, joined with its first Guard's
`aiProvider[0]`. Per-row:

- **Smoke test** — run benign / injection / PII probes inline, see HTTP code,
  latency, and scanner verdict (`passed` / `blocked`).
- **Delete** — removes both the Flow and the matching Guard.

Useful for partner self-service ongoing tenant management (after the SE has
left).

---

## Why this exists

FortiAIGate 8.0.0 has no per-Flow API key binding — there's a single global
inbound Bearer (Settings → API Keys). The MSSP isolation model is therefore
**secret-in-path**: each tenant gets an unguessable path prefix (e.g.
`/v1/customer1/a7176006f182a71d/chat/completions`) and the gateway routes
to that tenant's Flow + Guard + upstream.

Per-Flow Bearer scoping ("Virtual Keys") ships in **8.0.2** per the PM
session 2026-05-13. This tool will pick that up automatically once the
gateway exposes the `FlowDTO.authentication.allowedKeys` field.

Source of truth for the underlying API shape: the
[FortiAIGate SDK](https://github.com/howardsinc/FortiAIGate-SDK)
sibling repo, especially `api/reference/02-flows.md` and
`api/examples/05-onboard-tenant.sh`.

---

## Architecture

```
start.bat / start.ps1     <─ launcher; bootstraps uv + Python + deps
└─ uv run python -m app.main
   └─ FastAPI on 127.0.0.1:8765
      ├─ /            → static/index.html (Alpine.js SPA)
      ├─ /api/connect    → POST creds, server-side cookie session
      ├─ /api/tenants    → GET list / POST create / DELETE
      ├─ /api/providers  → curated provider+model catalog
      └─ /api/scanners   → scanner metadata for Custom mode
```

**Secrets handling:** the gateway URL is persisted to
`%APPDATA%\FortiAIGate-Onboarder\config.json`. Admin password and upstream
API keys are kept in memory only and are never written to disk. They live in
the in-process session keyed by an HttpOnly cookie; restart the launcher and
you re-authenticate.

**Self-signed certs:** the FortiAIGate appliance ships a self-signed cert.
The tool's httpx client runs with `verify=False`. Acceptable because this is
a single-user admin tool on a partner's machine reaching a known gateway over
private LAN — but **don't expose port 8765 to anyone but localhost**.

---

## Roadmap

- [ ] `tools/` tab to view/rotate the global Bearer
- [ ] Per-Flow Bearer support once gateway 8.0.2 lands
- [ ] Token cost dashboards (uses `tokenPricingEnabled` already set in Guard)
- [ ] PyInstaller single-exe build for partners who can't `git clone`
- [ ] System tray icon (pystray) so the launcher minimises out of the way

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

This is a Fortinet SE-team tool. PRs welcome. Issues / feature asks go in
GitHub Issues.
