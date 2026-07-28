#!/usr/bin/env python3
"""REPOS entrypoint — configure stack / build base image / update repos.

Usage:
  python3 configure.py                 # interactive stack configuration dialog
  python3 configure.py --config X.toml # seed dialog from an existing config
  python3 configure.py --base          # build the shared base image
  python3 configure.py --gitupdate     # git pull all repo-type modules
  python3 configure.py --base --gitupdate   # both
"""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path

# functions/ hosts all the config_* modules plus fly.py
sys.path.insert(0, str(Path(__file__).resolve().parent / "functions"))

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from config_base import BaseConfig, load_base_defaults, run_base_dialog
from config_modules import load_modules, run_module_selection
from config_env import run_env_dialog
from config_build import (
    build_base_image,
    choose_engine,
    ensure_repo,
    generate_all,
    run_hooks,
    save_stack_config,
)

ROOT = Path(__file__).resolve().parent
CONFIGS_ROOT = ROOT / "CONFIGS"


def load_seed(path: Path) -> dict:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text())


def do_gitupdate(workspace: Path, dry_run: bool) -> None:
    for mod in load_modules():
        if mod.kind == "repo" and mod.source and mod.target_dir:
            ensure_repo(mod, workspace, depth=1, update=True, dry_run=dry_run)


def do_base_build(engine: str, base_tag: str, dry_run: bool) -> int:
    defaults = load_base_defaults()
    base = BaseConfig(
        stack="base", container_name="repos-base", hostname="repos-base",
        image_tag=base_tag, network="host",
        base_image=defaults.base_image, base_requirements=list(defaults.base_requirements),
        container_prefix=defaults.container_prefix, image_registry=defaults.image_registry,
        include_thirdparty=defaults.include_thirdparty, module_exclude=list(defaults.module_exclude),
        volume_paths=list(defaults.volume_paths),
    )
    return build_base_image(choose_engine(engine), base_tag, base=base, dry_run=dry_run)


def do_stack_config(args) -> int:
    data = load_seed(args.config) if args.config else {}
    if data:
        print(f"[seed] {args.config}")

    meta = data.get("meta", {})
    seed = {k: str(v) for k, v in meta.items()}
    seed_sel = {str(x).strip() for x in data.get("selected_modules", []) if str(x).strip()} or None
    seed_env = OrderedDict((str(k), str(v)) for k, v in data.get("env", {}).items()) or None
    seed_ports = [str(x).strip() for x in data.get("publish_ports", []) if str(x).strip()] or None
    pers = data.get("persistence", {})
    seed_pers = {str(x).strip() for x in (pers.get("paths", []) if isinstance(pers, dict) else [])} or None

    base = run_base_dialog(load_base_defaults(), seed=seed)
    modules = run_module_selection(base, modules=load_modules(), seed_selected=seed_sel)
    env = run_env_dialog(base, modules, seed_env=seed_env, seed_ports=seed_ports,
                         seed_persistence=seed_pers, seed_meta=dict(meta) or None)
    hooks = run_hooks(base, modules, env)

    workspace = ROOT.parent
    result = generate_all(base, modules, env, engine=args.engine, workspace=workspace,
                          base_tag=args.base_tag, generate_only=True, dry_run=args.dry_run,
                          hook_results=hooks)

    save_stack_config(CONFIGS_ROOT / f"{base.stack}.toml", base=base, modules=modules,
                      env=env, workspace=workspace)
    return result


def main() -> int:
    p = argparse.ArgumentParser(
        description="Configure REPOS stack / build base / update repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--config", type=Path, help="Existing config TOML as seed for the dialog")
    p.add_argument("--engine", default="auto", help="Container engine: auto|podman|docker")
    p.add_argument("--base-tag", default="localhost/repos-base:latest")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--base", action="store_true", help="Build shared base image")
    p.add_argument("--gitupdate", action="store_true", help="git pull all repo modules")
    args = p.parse_args()

    workspace = ROOT.parent

    # Housekeeping flags run before the dialog and don't imply it
    if args.gitupdate:
        do_gitupdate(workspace, args.dry_run)

    if args.base:
        rc = do_base_build(args.engine, args.base_tag, args.dry_run)
        if rc != 0:
            return rc

    # If user explicitly requested --base or --gitupdate, skip the dialog
    if args.base or args.gitupdate:
        return 0

    return do_stack_config(args)


if __name__ == "__main__":
    raise SystemExit(main())
