#!/usr/bin/env python3
"""
Standalone setup for this project.
If CLAWBRIDGE is present as a sibling, installs into its central venv.
Otherwise creates a local venv.

Usage:
    python3 bin/setup.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR  = Path(__file__).resolve().parent.parent
CENTRAL_VENV = PROJECT_DIR.parent / "CLAWBRIDGE" / "venv"
LOCAL_VENV   = PROJECT_DIR / "venv"


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    if CENTRAL_VENV.exists():
        venv = CENTRAL_VENV
        print(f"CLAWBRIDGE venv found — installing into central venv: {venv}")
    else:
        venv = LOCAL_VENV
        if not venv.exists():
            print(f"Creating local venv at {venv} ...")
            run([sys.executable, "-m", "venv", str(venv)])
        else:
            print(f"Using existing local venv: {venv}")

    pip = venv / "bin" / "pip"
    run([str(pip), "install", "--upgrade", "pip", "-q"])

    req = PROJECT_DIR / "requirements.txt"
    if req.exists():
        print(f"Installing {req} ...")
        run([str(pip), "install", "-r", str(req)])
    else:
        print("No requirements.txt found — nothing to install.")

    print(f"\n✅  Done. Venv: {venv}")


if __name__ == "__main__":
    main()
