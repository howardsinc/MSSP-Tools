#!/usr/bin/env python3
"""
List Entitlements (serial numbers) - READ-ONLY

Shows every entitlement under your FortiFlex program: serial number, status,
configuration, description and whether its VM license token has been used.
Nothing is changed. Tokens are hidden unless you ask for them.

Usage:
    python list_entitlements.py                          # all accounts, all configs
    python list_entitlements.py --account-id 12345       # one customer account
    python list_entitlements.py --config-id 1001 --config-id 1002
    python list_entitlements.py --status ACTIVE          # PENDING | ACTIVE | STOPPED | EXPIRED
    python list_entitlements.py --filter "sdwan"         # substring of description or config name
    python list_entitlements.py --show-tokens            # prints license tokens - not on a screen share
    python list_entitlements.py --json > entitlements.json

Credentials are read from testing/config/credentials.json (see
documentation/CREDENTIALS_SETUP.md). They are never printed.
"""

import sys
import os
import json
import argparse
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token  # noqa: E402


def load_credentials():
    """Load API credentials from the toolkit's single credentials file."""
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )
    if not os.path.exists(config_file):
        print("[ERROR] testing/config/credentials.json not found - "
              "see documentation/CREDENTIALS_SETUP.md")
        sys.exit(1)
    with open(config_file, 'r') as f:
        return json.load(f)['fortiflex']


def build_config_index(client: FortiFlexClient, account_id=None):
    """Map configId -> {name, productType, accountId} so rows are readable."""
    result = client.list_configs(account_id=account_id)
    index = {}
    for cfg in result.get('configs', []):
        product = cfg.get('productType') or {}
        if isinstance(product, dict):
            product = product.get('name', '')
        index[cfg.get('id')] = {
            'name': cfg.get('name', ''),
            'product': product,
            'account_id': cfg.get('accountId'),
            'status': cfg.get('status', ''),
        }
    return index


def fetch_entitlements(client: FortiFlexClient, account_id=None, config_ids=None):
    """Return the raw entitlement rows for the chosen account / configs."""
    rows = []
    if config_ids:
        for cid in config_ids:
            result = client.list_entitlements(account_id=account_id, config_id=cid)
            rows.extend(result.get('entitlements', []))
    else:
        result = client.list_entitlements(account_id=account_id)
        rows.extend(result.get('entitlements', []))

    # De-duplicate on serial in case filters overlap
    seen, unique = set(), []
    for row in rows:
        sn = row.get('serialNumber')
        if sn and sn in seen:
            continue
        seen.add(sn)
        unique.append(row)
    return unique


def main():
    parser = argparse.ArgumentParser(description='List FortiFlex entitlements (read-only)')
    parser.add_argument('--account-id', type=int, help='Customer account ID (default: all accounts)')
    parser.add_argument('--config-id', type=int, action='append',
                        help='Configuration ID filter; repeat for several')
    parser.add_argument('--status', help='PENDING, ACTIVE, STOPPED or EXPIRED')
    parser.add_argument('--filter', help='Substring of description or config name (case-insensitive)')
    parser.add_argument('--show-tokens', action='store_true', help='Print VM license tokens')
    parser.add_argument('--json', action='store_true', help='Emit JSON instead of a table')
    args = parser.parse_args()

    creds = load_credentials()
    token = get_oauth_token(creds['api_username'], creds['api_password'],
                            creds.get('client_id', 'flexvm'))
    client = FortiFlexClient(token, creds['program_serial_number'])

    account_id = args.account_id or creds.get('account_id')
    configs = build_config_index(client, account_id=None)   # all accounts, for names
    rows = fetch_entitlements(client, account_id=account_id, config_ids=args.config_id)

    # Enrich + filter
    out = []
    for e in rows:
        cfg = configs.get(e.get('configId'), {})
        item = {
            'serialNumber': e.get('serialNumber'),
            'status': e.get('status'),
            'configId': e.get('configId'),
            'configName': cfg.get('name', ''),
            'product': cfg.get('product', ''),
            'accountId': e.get('accountId') or cfg.get('account_id'),
            'description': e.get('description') or '',
            'tokenStatus': e.get('tokenStatus') or '',
            'startDate': e.get('startDate') or '',
            'endDate': e.get('endDate') or '',
        }
        if args.show_tokens:
            item['token'] = e.get('token') or ''

        if args.status and (item['status'] or '').upper() != args.status.upper():
            continue
        if args.filter:
            hay = f"{item['description']} {item['configName']}".lower()
            if args.filter.lower() not in hay:
                continue
        out.append(item)

    out.sort(key=lambda r: (r['configName'], r['serialNumber'] or ''))

    if args.json:
        print(json.dumps(out, indent=2))
        return

    print(f"\n{'=' * 120}")
    print(f"ENTITLEMENTS  program={creds['program_serial_number']}  "
          f"account={account_id or 'ALL'}  rows={len(out)}")
    print(f"{'=' * 120}")
    hdr = f"{'SERIAL':<20} {'STATUS':<8} {'CONFIG':<8} {'CONFIG NAME':<30} {'TOKEN':<8} {'DESCRIPTION'}"
    print(hdr)
    print('-' * 120)
    for r in out:
        print(f"{(r['serialNumber'] or ''):<20} {(r['status'] or ''):<8} "
              f"{str(r['configId'] or ''):<8} {r['configName'][:30]:<30} "
              f"{r['tokenStatus']:<8} {r['description'][:50]}")
        if args.show_tokens and r.get('token'):
            print(f"{'':<20} token: {r['token']}")

    counts = Counter(r['status'] for r in out)
    print('-' * 120)
    print('By status: ' + ', '.join(f"{k}={v}" for k, v in sorted(counts.items())))
    print('ACTIVE entitlements bill points every day; PENDING ones are free until their token is applied.')


if __name__ == '__main__':
    main()
