#!/usr/bin/env python3
"""Non-interactive build runner for REPOS web UI.

Reads a JSON config from a file, runs generate_all() programmatically,
and optionally executes the generated build script.

Usage:
    python3 webapi_build.py config.json              # generate only
    python3 webapi_build.py config.json --build       # generate + build
    python3 webapi_build.py --base                    # build base image
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_base import BaseConfig, load_base_defaults
from config_modules import (
    ModuleSelection,
    apply_dependencies,
    load_modules,
    module_map,
)
from config_env import EnvConfig
from config_build import (
    build_base_image,
    choose_engine_safe,
    generate_all,
    run_hooks,
    save_stack_config,
)

ROOT = Path(__file__).resolve().parent.parent
CONFIGS_ROOT = ROOT / "CONFIGS"


def build_from_json(config: dict, *, do_build: bool = False) -> int:
    """Run a full generate (and optionally build) from a JSON config dict."""
    defaults = load_base_defaults()
    meta = config.get("meta", {})

    base = BaseConfig(
        stack=meta.get("stack", "web-stack"),
        container_name=meta.get("container_name", f"{defaults.container_prefix}web-stack"),
        hostname=meta.get("hostname", "web-stack"),
        image_tag=meta.get("image_tag", f"{defaults.image_registry}web-stack:latest"),
        network=meta.get("network", defaults.network),
        base_image=defaults.base_image,
        base_requirements=list(defaults.base_requirements),
        container_prefix=meta.get("container_prefix", defaults.container_prefix),
        image_registry=meta.get("image_registry", defaults.image_registry),
        include_thirdparty=defaults.include_thirdparty,
        module_exclude=list(defaults.module_exclude),
        volume_paths=list(defaults.volume_paths),
    )

    all_modules = load_modules()
    by_name = module_map(all_modules)

    selected_names = set(config.get("selected_modules", []))
    selected_names = apply_dependencies(selected_names, by_name)
    explicit = set(config.get("selected_modules", []))
    forced = sorted(x for x in selected_names if x not in explicit)

    modules = ModuleSelection(
        selected=sorted(selected_names),
        explicit=sorted(explicit),
        forced=forced,
        modules=by_name,
        all_modules=all_modules,
    )

    # Build env config
    env_raw = config.get("env", {})
    env_values = OrderedDict((str(k), str(v)) for k, v in env_raw.items())
    publish_ports = [str(x) for x in config.get("publish_ports", [])]
    persistence_paths = [str(x) for x in config.get("persistence_paths", [])]

    # Collect persistence from modules if not specified
    if not persistence_paths:
        for name in modules.selected:
            mod = by_name.get(name)
            if not mod:
                continue
            for p in mod.persistence:
                if p not in persistence_paths:
                    persistence_paths.append(p)
            for p, enabled in mod.volume_defaults.items():
                if enabled and p not in persistence_paths:
                    persistence_paths.append(p)
        if "/etc/supervisor/conf.d" not in persistence_paths:
            persistence_paths.append("/etc/supervisor/conf.d")

    litellm_mode = meta.get("litellm_mode", "external")
    litellm_local_port = int(meta.get("litellm_local_port", 4000))

    env = EnvConfig(
        env_values=env_values,
        publish_ports=publish_ports,
        persistence_paths=persistence_paths,
        litellm_required="litellm" in {n.lower() for n in modules.selected},
        litellm_mode=litellm_mode,
        litellm_local_port=litellm_local_port,
        tailscale_enabled="tailscale" in {n.lower() for n in modules.selected},
    )

    hooks = run_hooks(base, modules, env)
    workspace = ROOT.parent
    engine = meta.get("engine", "auto")

    result = generate_all(
        base, modules, env,
        engine=engine,
        workspace=workspace,
        generate_only=not do_build,
        dry_run=False,
        hook_results=hooks,
    )

    CONFIGS_ROOT.mkdir(parents=True, exist_ok=True)
    save_stack_config(
        CONFIGS_ROOT / f"{base.stack}.toml",
        base=base, modules=modules, env=env, workspace=workspace,
    )

    return result


def do_base_build(engine: str = "auto") -> int:
    defaults = load_base_defaults()
    base_tag = "localhost/repos-base:latest"
    base = BaseConfig(
        stack="base", container_name="repos-base", hostname="repos-base",
        image_tag=base_tag, network="host",
        base_image=defaults.base_image, base_requirements=list(defaults.base_requirements),
        container_prefix=defaults.container_prefix, image_registry=defaults.image_registry,
        include_thirdparty=defaults.include_thirdparty, module_exclude=list(defaults.module_exclude),
        volume_paths=list(defaults.volume_paths),
    )
    return build_base_image(choose_engine_safe(engine), base_tag, base=base, dry_run=False)


def main() -> int:
    p = argparse.ArgumentParser(description="REPOS non-interactive build runner")
    p.add_argument("config_file", nargs="?", type=Path, help="JSON config file")
    p.add_argument("--build", action="store_true", help="Also run container build")
    p.add_argument("--base", action="store_true", help="Build shared base image")
    p.add_argument("--engine", default="auto")
    args = p.parse_args()

    if args.base:
        return do_base_build(args.engine)

    if not args.config_file:
        p.error("config_file required when not using --base")

    config = json.loads(args.config_file.read_text())
    config.setdefault("meta", {})["engine"] = args.engine
    return build_from_json(config, do_build=args.build)


if __name__ == "__main__":
    raise SystemExit(main())
