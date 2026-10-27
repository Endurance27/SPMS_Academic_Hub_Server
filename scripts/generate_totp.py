#!/usr/bin/env python3
"""
Generate TOTP code from a secret for testing purposes.
Usage: python scripts/generate_totp.py <totp_secret>
"""
import sys
import pyotp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if len(sys.argv) > 1:
    secret = sys.argv[1]
else:
    print("Usage: python scripts/generate_totp.py <totp_secret>")
    print("Example: python scripts/generate_totp.py BJRLGV5BV3X7G4JXTSBDRLW56AIG7EDR")
    sys.exit(1)

# Generate TOTP code
totp = pyotp.TOTP(secret)
code = totp.now()

print(f"TOTP Secret: {secret}")
print(f"Current TOTP Code: {code}")
