#!/usr/bin/env python3
"""
Create VM Entitlements (FortiGate-VM / FortiManager-VM / FortiAnalyzer-VM licenses)

PLAN FIRST, THEN EXECUTE. Without --execute this script only shows what it
would create and exits. New entitlements start PENDING and cost nothing until
the token is applied on a device (FortiOS: `execute vm-license <token>`).

Usage:
    # 1. Plan (no change): resolves the config, shows product, count, description
    python create_vm_entitlements.py --config-id 1001 --count 2 --description "Lab spoke-3"

    # 2. Execute: creates them, prints the new serial numbers (tokens stay hidden)
    python create_vm_entitlements.py --config-id 1001 --count 2 --description "Lab spoke-3" --execute

    # Save the tokens somewhere gitignored instead of printing them
    python create_vm_entitlements.py ... --execute --token-file ../../my-tokens.jsonl

    # Print tokens on screen (not on a screen share)
    python create_vm_entitlements.py ... --execute --show-tokens

Before creating, run `python list_entitlements.py --config-id 1001 --status PENDING`:
unused PENDING entitlements already exist more often than you think.

Credentials are read from testing/config/credentials.json and never printed.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fortiflex_client import FortiFlexClient, get_oauth_token  # noqa: E402

VM_PRODUCT_HINTS = ('vm', 'virtual')


def load_credentials():
    config_file = os.path.join(
        os.path.dirname(__file__), '..', 'testing', 'config', 'credentials.json'
    )
    if not os.path.exists(config_file):
        print("[ERROR] testing/config/credentials.json not found - "
              "see documentation/CREDENTIALS_SETUP.md")
        sys.exit(1)
    with open(config_file, 'r') as f:
        return json.load(f)['fortiflex']


def resolve_config(client: FortiFlexClient, config_id: int):
    """Find the configuration across all accounts; return its dict or None."""
    for cfg in client.list_configs().get('configs', []):
        if cfg.get('id') == config_id:
            return cfg
    return None


def main():
    parser = argparse.ArgumentParser(description='Create FortiFlex VM entitlements (plan first)')
    parser.add_argument('--config-id', type=int, required=True, help='Configuration ID (VM product type)')
    parser.add_argument('--count', type=int, default=1, help='How many to create (default 1)')
    parser.add_argument('--description', help='Description stamped on each entitlement (recommended)')
    parser.add_argument('--end-date', help='YYYY-MM-DD; default = program end date')
    parser.add_argument('--execute', action='store_true', help='Actually create. Without it: plan only')
    parser.add_argument('--token-file', help='Append {serial, token, ...} JSON lines here (gitignored path!)')
    parser.add_argument('--show-tokens', action='store_true', help='Print tokens on screen')
    args = parser.parse_args()

    if args.count < 1 or args.count > 50:
        print('[ERROR] --count must be between 1 and 50')
        sys.exit(2)

    creds = load_credentials()
    token = get_oauth_token(creds['api_username'], creds['api_password'],
                            creds.get('client_id', 'flexvm'))
    client = FortiFlexClient(token, creds['program_serial_number'])

    cfg = resolve_config(client, args.config_id)
    if not cfg:
        print(f"[ERROR] Config {args.config_id} not found in program {creds['program_serial_number']}. "
              f"Run `python list_configs.py` to see the IDs.")
        sys.exit(1)

    product = cfg.get('productType') or {}
    product_name = product.get('name', '') if isinstance(product, dict) else str(product)

    print(f"\n{'=' * 80}")
    print('PLAN' if not args.execute else 'EXECUTE')
    print(f"{'=' * 80}")
    print(f"Program:      {creds['program_serial_number']}")
    print(f"Config:       {cfg.get('id')}  {cfg.get('name')}  [{cfg.get('status')}]")
    print(f"Product:      {product_name}")
    print(f"Account:      {cfg.get('accountId')}")
    print(f"Count:        {args.count}")
    print(f"Description:  {args.description or '(none - consider setting one)'}")
    print(f"End date:     {args.end_date or 'program end date'}")

    if cfg.get('status', '').upper() != 'ACTIVE':
        print(f"\n[STOP] Config status is {cfg.get('status')}; enable it first (use_case_3 / enable_config).")
        sys.exit(1)
    if product_name and not any(h in product_name.lower() for h in VM_PRODUCT_HINTS):
        print(f"\n[WARN] Product '{product_name}' does not look like a VM type. "
              f"Hardware uses create_hardware_entitlements, cloud services create_cloud_entitlements.")

    if not args.execute:
        print('\nNothing created. Re-run with --execute to create these entitlements.')
        return

    result = client.create_vm_entitlements(
        config_id=args.config_id, count=args.count,
        description=args.description, end_date=args.end_date,
    )
    rows = result.get('entitlements', [])
    if result.get('status') not in (0, None) or not rows:
        print(f"\n[ERROR] API returned status={result.get('status')} message={result.get('message')}")
        sys.exit(1)

    print(f"\nCreated {len(rows)} entitlement(s):")
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    for e in rows:
        print(f"  {e.get('serialNumber')}  status={e.get('status')}  config={e.get('configId')}  "
              f"end={e.get('endDate')}")
        if args.show_tokens:
            print(f"      token: {e.get('token')}")
        if args.token_file:
            with open(args.token_file, 'a') as fh:
                fh.write(json.dumps({
                    'serialNumber': e.get('serialNumber'),
                    'token': e.get('token'),
                    'configId': e.get('configId'),
                    'description': args.description,
                    'created': stamp,
                }) + '\n')

    if args.token_file:
        print(f"\nTokens appended to {args.token_file} - keep that file out of git.")
    elif not args.show_tokens:
        print('\nTokens were not shown. Fetch one later with client.get_vm_token(<serial>) '
              'or re-run list_entitlements.py --show-tokens.')
    print('These are PENDING: no points are charged until `execute vm-license <token>` runs on a device.')


if __name__ == '__main__':
    main()
