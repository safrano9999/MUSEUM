#!/usr/bin/env python3
"""
CLAWBRIDGE central setup
Creates the shared venv and installs dependencies from all sibling projects.

Usage:
    python3 bin/setup.py
"""

import subprocess
import sys
from pathlib import Path

BRIDGE_DIR   = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BRIDGE_DIR.parent
VENV_DIR     = BRIDGE_DIR / "venv"

# Core deps required by CLAWBRIDGE itself
CORE_DEPS = ["python-telegram-bot>=20.0", "python-dotenv"]


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    # Create central venv if it doesn't exist
    if not VENV_DIR.exists():
        print(f"Creating central venv at {VENV_DIR} ...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"Using existing venv at {VENV_DIR}")

    pip = VENV_DIR / "bin" / "pip"
    run([str(pip), "install", "--upgrade", "pip", "-q"])

    # CLAWBRIDGE core deps
    print(f"\n[CLAWBRIDGE] installing core deps ...")
    run([str(pip), "install"] + CORE_DEPS)

    # All sibling project deps (root and bin/ subfolders)
    reqs = sorted(set(PROJECTS_DIR.glob("*/requirements.txt")) |
                  set(PROJECTS_DIR.glob("*/bin/requirements.txt")))
    for req in reqs:
        project = req.parent if req.parent.name != "bin" else req.parent.parent
        if project == BRIDGE_DIR:
            continue
        print(f"\n[{project.name}] installing {req}")
        run([str(pip), "install", "-r", str(req)])

    print(f"\n✅  Central venv ready: {VENV_DIR}")
    print(f"    Activate : source {VENV_DIR}/bin/activate")
    print(f"    Or just run: bin/clawbridge.sh  (activates automatically)")

    # Check credential files (discover all *env.example across all projects)
    print()
    for example in sorted(PROJECTS_DIR.glob("**/*nv.example")):
        stem = example.name.replace(".example", "")
        local_file  = example.parent / stem
        # Accept both 'env' and '.env' in CLAWBRIDGE (centrally stored)
        central     = BRIDGE_DIR / stem
        central_dot = BRIDGE_DIR / f".{stem}"
        if local_file.exists():
            print(f"✅  {example.parent.name}/{stem}")
        elif central.exists() or central_dot.exists():
            found = central if central.exists() else central_dot
            print(f"✅  {example.parent.name}/{stem}  (centrally in CLAWBRIDGE/{found.name})")
        else:
            print(f"⚠️   Missing: cd {example.parent} && cp {example.name} {stem}")


if __name__ == "__main__":
    main()
