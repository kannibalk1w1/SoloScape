#!/usr/bin/env python3
"""Import a stopped world copy without touching original saves or password hashes."""
import argparse
import getpass
import json
import profiles

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('saves_copy', help='Independent copy of the stopped server saves directory')
parser.add_argument('--label', required=True)
parser.add_argument('--account', required=True)
parser.add_argument('--remember-password', action='store_true', help='Prompt privately for existing native login password; otherwise use normal in-game login')
args = parser.parse_args()
password = getpass.getpass('Existing native login password: ') if args.remember_password else ''
profile = profiles.import_world_copy(args.saves_copy, args.label, args.account, password)
print(json.dumps(profile.metadata(), indent=2))
