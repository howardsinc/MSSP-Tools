# FortiFlex MSSP Toolkit: notes for AI coding agents

You are in a Python toolkit that drives the Fortinet FortiFlex v2 API for an MSSP program:
license configurations, entitlements (the licenses themselves, one serial number each), points
consumption and multi-tenant views. The full agent skill is
[skills/fortiflex-mssp/SKILL.md](skills/fortiflex-mssp/SKILL.md). Read it before your first API call.

## Read in this order

1. `skills/fortiflex-mssp/SKILL.md` (how the API and this client fit together, the rules)
2. `documentation/GETTING_STARTED.md` and `documentation/CREDENTIALS_SETUP.md`
3. `src/fortiflex_client.py` (one class, one method per endpoint)
4. `documentation/USE_CASES_GUIDE.md` and `examples/` when you need a workflow

## Rules

- Credentials live only in `testing/config/credentials.json` (gitignored). Never print, log, echo
  or commit the password, a token, an account ID, a program serial or an entitlement serial. This
  repository is public. `python testing/test_authentication.py` proves login without showing secrets.
- Read first. `examples/list_configs.py` and `examples/list_entitlements.py` are read-only.
- Plan, show the plan, then execute only on the owner's go. `examples/create_vm_entitlements.py`
  does nothing without `--execute`.
- Billing: an ACTIVE entitlement bills points every day. A PENDING one is free until its token is
  applied. `entitlements/stop` ends billing the next day and is reversible with
  `entitlements/reactivate`.
- Pick the create call by product: VM appliances `create_vm_entitlements`, hardware with a serial
  `create_hardware_entitlements`, cloud services `create_cloud_entitlements`.
- Do not switch logging to DEBUG while handling entitlements: the client logs full payloads and
  responses, tokens included.
- One failed login is enough: a wrong password locks the API user (HTTP 423). Check the
  credentials file instead of retrying.

## Commands

```
python testing/test_authentication.py                     # login + program access, no secrets shown
python examples/list_configs.py                           # configuration IDs and names
python examples/list_entitlements.py --status ACTIVE      # serial numbers, read-only
python examples/create_vm_entitlements.py --config-id <id> --count 1 --description "<who/what>"   # plan
python examples/create_vm_entitlements.py ... --execute --token-file <gitignored path>            # create
```
