---
name: fortiflex-mssp
description: Work the Fortinet FortiFlex v2 API through the fortiflex-mssp-toolkit - list license entitlements (serial numbers), create FortiGate-VM / FortiManager-VM / FortiAnalyzer-VM licenses, stop or reactivate them, read points consumption. Use when asked about FortiFlex, flex licenses, entitlements, VM license tokens, "execute vm-license", or MSSP program points.
---

# FortiFlex MSSP toolkit: agent skill

This skill is self-contained and public. It names no customer, program, account or serial. Those
values come from the owner's `testing/config/credentials.json` and from the owner's own notes.

## 1. What FortiFlex is, in four lines

- A **program** (serial `ELAVMS...`) is the MSSP's licensing contract. Postpaid programs bill
  points monthly for what was ACTIVE each day.
- A **configuration** (`configId`) is a license shape: product type (FortiGate-VM 2 CPU, FortiGate
  hardware, FortiClient EMS Cloud, ...) plus its add-ons. Configs belong to a customer **account**.
- An **entitlement** is one license made from a config. It has a serial number, a status
  (`PENDING`, `ACTIVE`, `STOPPED`, `EXPIRED`) and, for VMs, a **token** that a device redeems with
  `execute vm-license <token>`. Redeeming turns PENDING into ACTIVE and starts daily billing.
- **Stop** ends billing the next day and keeps the serial; **reactivate** resumes it.

## 2. The API

| Step | Call |
|---|---|
| Login | `POST https://customerapiauth.fortinet.com/api/v1/oauth/token/` body `{username, password, client_id: "flexvm", grant_type: "password"}`. Response `access_token` lives about an hour. |
| Base URL | `https://support.fortinet.com/ES/api/fortiflex/v2`, every call is `POST` with JSON and `Authorization: Bearer <token>`. A good response has `"status": 0`. |
| Programs | `programs/list`; `programs/points` (prepaid balance only) |
| Configs | `configs/list` `{programSerialNumber, accountId?}`; `configs/create`, `configs/update`, `configs/disable`, `configs/enable` |
| Entitlements, read | `entitlements/list` `{programSerialNumber, accountId?, configId?, serialNumber?}`; `entitlements/points` for consumption |
| Entitlements, create | `entitlements/vm/create` `{configId, count, description?, endDate?}` for VM appliances; `entitlements/hardware/create` `{configId, serialNumbers[]}`; `entitlements/cloud/create` `{configId, count}` for cloud services |
| Entitlements, change | `entitlements/update` `{serialNumber, configId, description?, endDate?}`; `entitlements/stop` and `entitlements/reactivate` `{serialNumber}`; `entitlements/vm/token` `{serialNumber, regenerateToken?}` |

In `src/fortiflex_client.py` these are `get_oauth_token(...)`, then `FortiFlexClient(token,
program_sn)` with `list_configs`, `list_entitlements`, `create_vm_entitlements`,
`create_hardware_entitlements`, `create_cloud_entitlements`, `update_entitlement`,
`stop_entitlement`, `reactivate_entitlement`, `get_vm_token`, `get_entitlement_points`,
`get_program_points`, `get_multi_tenant_view`.

## 3. Credentials

Single file: `testing/config/credentials.json`, key `fortiflex` with `api_username`,
`api_password`, `client_id` (`flexvm`), `program_serial_number`, `account_id`. Every script loads
it; nothing else needs editing. Prove it works with `python testing/test_authentication.py`.

Never print, log, paste or commit the password, a bearer token, a license token, the program
serial, an account ID or an entitlement serial. The repository that holds this toolkit is public.
When you must show the owner a list, show it in the terminal, not in a commit or a document.

## 4. The four jobs

**List serial numbers (read-only)**

```
python examples/list_entitlements.py                       # everything
python examples/list_entitlements.py --config-id <id> --status PENDING
python examples/list_entitlements.py --filter "<description or config text>"
python examples/list_entitlements.py --json > <gitignored file>
```

In code: `client.list_entitlements(config_id=<id>)["entitlements"]`. Pass `account_id` when the
program has several customer accounts and you want one of them.

**Create VM licenses (plan, then execute)**

1. List PENDING entitlements for that config first. Unused spares are common; use them before
   making more.
2. `python examples/create_vm_entitlements.py --config-id <id> --count <n> --description "<site or device>"`
   prints the plan and stops.
3. On the owner's go, add `--execute`, and `--token-file <gitignored path>` so tokens land in a
   file instead of the screen. The script prints the new serials.
4. The device redeems a token with `execute vm-license <token>`; the entitlement turns ACTIVE on
   its next FortiGuard contact.

In code: `client.create_vm_entitlements(config_id, count, description)` returns
`result["entitlements"]`, each with `serialNumber` and `token`.

**Stop or reactivate**

`client.stop_entitlement("<serial>")` then read it back with
`client.list_entitlements(serial_number="<serial>")`. Billing ends the next day. Undo with
`client.reactivate_entitlement("<serial>")`. `examples/use_case_5_entitlement_suspension_v2.py`
wraps this for a whole customer.

**Consumption**

`examples/consumption_report_v2.py` (daily and monthly points) and
`examples/use_case_7_program_balance_monitoring.py`. `programs/points` only answers for prepaid
programs; a postpaid program reads consumption from `entitlements/points`.

## 5. Rules

- Read before write. Show the plan (config, product, count, description, which serials) and wait
  for the owner's go. Stop is reversible; create is not deletable, only stoppable.
- Verify effects, not responses: after a create or stop, list the serial back and report its
  status.
- Description every entitlement you create with who or what it is for. Undescribed ACTIVE
  entitlements are the ones that quietly bill for months.
- One wrong password locks the IAM API user (HTTP 423). Do not retry a failed login; check the
  file and tell the owner.
- Logging: the client logs full request and response bodies at DEBUG. Leave logging at INFO
  while tokens are in flight.
- Rate limits: about 100 calls a minute. The client has a `RateLimiter`; loops over many
  accounts should use it.
- Hardware entitlements need the device serial up front and bill from creation; VM and cloud
  entitlements bill from redemption.
- Points are charged per calendar day in Pacific time. A stop issued late in the day still pays
  for that day.

## 6. When you finish

Tell the owner, in a few lines: what you read, what you created or stopped (serials, in the
terminal only), what the list-back showed, and what is still PENDING or spare. Put any new trap
you hit into this file in the same sitting.
