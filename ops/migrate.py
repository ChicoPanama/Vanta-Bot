#!/usr/bin/env python3
"""Run database migrations (Phase 9)."""

import subprocess
import sys


def main():
    print("[*] Running: alembic upgrade head")
    try:
        subprocess.check_call(["alembic", "upgrade", "head"])
        print("✅ Migrations complete")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
