"""Step 4: Build generation — Dockerfile, .env, scripts, supervisor confs."""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

from config_base import BaseConfig
from config_modules import ModuleDef, ModuleSelection
from config_env import EnvConfig
from fly import generate_fly_artifacts

ROOT = Path(__file__).resolve().parent.parent
GENERATED_ROOT = ROOT / "generated"
DISABLED_RUNTIME_MODULES = {"openclaw", "hermes"}

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RuntimeProgram:
    name: str
    command: str
    directory: str
    autostart: bool = True
    autorestart: bool = True
    startsecs: int = 3
    priority: int = 200


@dataclasses.dataclass
class HookContext:
    base_config: BaseConfig
    env: OrderedDict[str, str]
    selected_modules: list[str]
    module_dir: Path


@dataclasses.dataclass
class HookResult:
    dockerfile_lines: list[str] = dataclasses.field(default_factory=list)
    env_additions: dict[str, str] = dataclasses.field(default_factory=dict)
    supervisor_confs: list[str] = dataclasses.field(default_factory=list)
    entrypoint_lines: list[str] = dataclasses.field(default_factory=list)
    runtime_command_override: str | None = None

    def append_dockerfile(self, line: str) -> None:
        self.dockerfile_lines.append(line)

    def append_env(self, key: str, value: str) -> None:
        self.env_additions[key] = value

    def set_runtime_command(self, cmd: str) -> None:
        self.runtime_command_override = cmd

    def append_supervisor_conf(self, block: str) -> None:
        self.supervisor_confs.append(block)

    def append_entrypoint(self, line: str) -> None:
        self.entrypoint_lines.append(line)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-._") or "stack"


def volume_suffix(path: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", path.strip("/")).strip("_").lower()
    return s or "root"


def run_cmd(cmd: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> None:
    where = str(cwd or Path.cwd())
    print(f"[run] ({where}) {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def choose_engine(requested: str) -> str:
    if requested in {"podman", "docker"}:
        return requested
    for candidate in ("podman", "docker"):
        if subprocess.run(["bash", "-lc", f"command -v {candidate} >/dev/null 2>&1"]).returncode == 0:
            return candidate
    raise RuntimeError("No container engine found (podman/docker)")


def choose_engine_safe(requested: str) -> str:
    if requested in {"podman", "docker"}:
        return requested
    try:
        return choose_engine(requested)
    except RuntimeError:
        return "podman"


def base_image_exists(engine: str, tag: str) -> bool:
    try:
        result = subprocess.run([engine, "image", "exists", tag], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Repo management
# ---------------------------------------------------------------------------

def ensure_repo(mod: ModuleDef, workspace: Path, *, depth: int, update: bool, dry_run: bool) -> Path:
    target = workspace / mod.target_dir
    if target.exists():
        if not (target / ".git").exists():
            raise RuntimeError(f"Target exists but is not git: {target}")
        if update:
            if not dry_run:
                subprocess.run(["git", "-C", str(target), "fetch", "--all", "-q"], check=False)
                subprocess.run(["git", "-C", str(target), "reset", "--hard", "origin/main"], capture_output=True, check=False)
                print(f"[update] {target}")
            else:
                print(f"[dry-run] git fetch + reset --hard {target}")
        else:
            print(f"[skip] repo exists: {target}")
        return target
    run_cmd(["git", "clone", "--depth", str(depth), mod.source, str(target)], dry_run=dry_run)
    return target


def resolve_thirdparty_source(rel_path: str, workspace: Path) -> Path | None:
    rel = Path(rel_path)
    for candidate in [workspace / rel, ROOT.parent / rel, Path.home() / rel, Path.home() / "safrano9999" / rel]:
        if candidate.exists():
            return candidate.resolve()
    return None


def resolve_ref_path(mod: ModuleDef, repo_root: Path, ref: str) -> Path | None:
    value = (ref or "").strip()
    if not value or value == "-":
        return None
    if value.startswith("@module/"):
        return (mod.module_dir / value[len("@module/"):]).resolve()
    return (repo_root / value).resolve()


# ---------------------------------------------------------------------------
# Runtime / Supervisor
# ---------------------------------------------------------------------------

def parse_runtime_programs(runtime_file: Path, module_name: str, target_dir: str) -> list[RuntimeProgram]:
    if not runtime_file.exists():
        return []
    data = tomllib.loads(runtime_file.read_text())
    runtime = data.get("runtime", data) if isinstance(data, dict) else {}
    if not isinstance(runtime, dict):
        return []

    out: list[RuntimeProgram] = []
    raw = runtime.get("programs", [])
    if isinstance(raw, list):
        for idx, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            command = str(item.get("command", "")).strip()
            if not command:
                continue
            name = re.sub(r"[^a-z0-9_-]+", "_", str(item.get("name", f"{module_name}_{idx}")).strip().lower())
            directory = str(item.get("directory", "")).strip() or f"/opt/{target_dir}"
            out.append(RuntimeProgram(
                name=name or f"{module_name}_{idx}",
                command=command,
                directory=directory,
                autostart=bool(item.get("autostart", True)),
                autorestart=bool(item.get("autorestart", True)),
                startsecs=int(item.get("startsecs", 3)),
                priority=int(item.get("priority", 200)),
            ))
    if out:
        return out

    commands = runtime.get("commands", [])
    if isinstance(commands, list):
        for idx, raw_cmd in enumerate(commands, start=1):
            cmd = str(raw_cmd).strip()
            if not cmd:
                continue
            out.append(RuntimeProgram(
                name=f"{module_name}_{idx}", command=cmd, directory=f"/opt/{target_dir}",
                autostart=True, autorestart=True, startsecs=2, priority=200 + idx,
            ))
    return out


def parse_runtime_persistence(runtime_file: Path) -> list[str]:
    if not runtime_file.exists():
        return []
    data = tomllib.loads(runtime_file.read_text())
    runtime = data.get("runtime", data) if isinstance(data, dict) else {}
    if not isinstance(runtime, dict):
        return []
    raw = runtime.get("persistent_paths", [])
    if isinstance(raw, str):
        raw = [raw]
    return [str(x).strip() for x in raw if isinstance(raw, list) and str(x).strip().startswith("/")]


def read_repo_module_persistence(module_file: Path) -> list[str]:
    if not module_file.exists():
        return []
    data = tomllib.loads(module_file.read_text())
    out: list[str] = []
    for item in data.get("persistence", []):
        if isinstance(item, dict):
            p = str(item.get("path", "")).strip()
            if p.startswith("/") and p not in out:
                out.append(p)
    return out


def write_supervisor_conf(path: Path, programs: list[RuntimeProgram]) -> None:
    lines: list[str] = []
    for p in sorted(programs, key=lambda x: (x.priority, x.name)):
        lines.extend([
            f"[program:{p.name}]",
            f"directory={p.directory}",
            f"command=/bin/bash -c {shlex.quote(p.command)}",
            f"autostart={'true' if p.autostart else 'false'}",
            f"autorestart={'true' if p.autorestart else 'false'}",
            f"startsecs={p.startsecs}",
            f"priority={p.priority}",
            "stdout_logfile=/dev/stdout",
            "stdout_logfile_maxbytes=0",
            "stderr_logfile=/dev/stderr",
            "stderr_logfile_maxbytes=0",
            "",
        ])
    if not programs:
        lines.append("# no runtime programs\n")
    path.write_text("\n".join(lines) + "\n")


def supervisor_target_dir(module_name: str) -> str:
    if module_name.strip().lower() in DISABLED_RUNTIME_MODULES:
        return "/etc/supervisor/conf.d/disabled"
    return "/etc/supervisor/conf.d"


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def run_hooks(
    base: BaseConfig,
    modules: ModuleSelection,
    env: EnvConfig,
) -> list[HookResult]:
    results: list[HookResult] = []
    for name in modules.selected:
        mod = modules.modules.get(name)
        if not mod:
            continue
        hook_file = mod.module_dir / "hook.py"
        if not hook_file.exists():
            continue
        ctx = HookContext(
            base_config=base,
            env=env.env_values,
            selected_modules=modules.selected,
            module_dir=mod.module_dir,
        )
        try:
            spec = importlib.util.spec_from_file_location(f"hook_{name}", hook_file)
            hook_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hook_mod)
            if hasattr(hook_mod, "on_configure"):
                result = hook_mod.on_configure(ctx)
                if isinstance(result, HookResult):
                    results.append(result)
                    print(f"[hook] {name}: ok")
        except Exception as e:
            print(f"[hook] {name}: error: {e}")
    return results


# ---------------------------------------------------------------------------
# File generators
# ---------------------------------------------------------------------------

def write_env_file(path: Path, env_values: OrderedDict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in env_values.items()]
    path.write_text("\n".join(lines) + ("\n" if lines else ""))


def write_run_script(
    path: Path, *, engine: str, image_tag: str, container_name: str,
    hostname: str, network: str, publish_ports: list[str],
    env_file: Path, persistent_paths: list[str],
) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f'ENGINE="${{ENGINE:-{engine}}}"',
        f'IMAGE="${{IMAGE:-{image_tag}}}"',
        f'CONTAINER_NAME="${{CONTAINER_NAME:-{container_name}}}"',
        f'HOSTNAME="${{HOSTNAME:-{hostname}}}"',
        f'NETWORK="${{NETWORK:-{network}}}"',
        f'ENV_FILE="${{ENV_FILE:-{env_file}}}"',
        "MOUNTS=()",
        "ENV_ARGS=()",
        'if [[ -f "${ENV_FILE}" ]]; then ENV_ARGS+=(--env-file "${ENV_FILE}"); fi',
        "PORT_ARGS=()",
    ]
    if network != "host":
        for mapping in publish_ports:
            lines.append(f'PORT_ARGS+=(-p "{mapping}")')
    for p in persistent_paths:
        lines.append(f'MOUNTS+=(--mount "type=volume,source=${{CONTAINER_NAME}}_{volume_suffix(p)},target={p}")')
    lines.extend([
        'if "$ENGINE" ps -a --format "{{.Names}}" | grep -Fxq "$CONTAINER_NAME"; then "$ENGINE" rm -f "$CONTAINER_NAME" >/dev/null; fi',
        'exec "$ENGINE" run --name "$CONTAINER_NAME" --hostname "$HOSTNAME" --network "$NETWORK" "${PORT_ARGS[@]}" "${MOUNTS[@]}" "${ENV_ARGS[@]}" "$IMAGE"',
        "",
    ])
    path.write_text("\n".join(lines))


def write_build_script(
    path: Path, *, engine: str, base_tag: str, image_tag: str,
    base_dockerfile: Path | None, base_repo: Path | None,
    overlay: Path, workspace: Path, use_shared_base: bool = False,
) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f'ENGINE="${{ENGINE:-{engine}}}"',
        f'BASE_TAG="${{BASE_TAG:-{base_tag}}}"',
        f'IMAGE="${{IMAGE:-{image_tag}}}"',
        f'OVERLAY_DOCKERFILE="${{OVERLAY_DOCKERFILE:-{overlay}}}"',
        f'WORKSPACE="${{WORKSPACE:-{workspace}}}"',
    ]
    if use_shared_base:
        lines.extend([
            'echo "[build] using shared base: ${BASE_TAG}"',
            'echo "[build] final image: ${IMAGE}"',
            '"$ENGINE" build -f "$OVERLAY_DOCKERFILE" -t "$IMAGE" "$WORKSPACE"',
        ])
    else:
        lines.extend([
            f'BASE_DOCKERFILE="${{BASE_DOCKERFILE:-{base_dockerfile or overlay}}}"',
            f'BASE_REPO="${{BASE_REPO:-{base_repo or workspace}}}"',
            '"$ENGINE" build -f "$BASE_DOCKERFILE" -t "$BASE_TAG" "$BASE_REPO"',
            '"$ENGINE" build -f "$OVERLAY_DOCKERFILE" -t "$IMAGE" "$WORKSPACE"',
        ])
    lines.append("")
    path.write_text("\n".join(lines))


def write_container_file(
    path: Path, *, image_tag: str, container_name: str, hostname: str,
    network: str, env_file: Path, publish_ports: list[str], persistent_paths: list[str],
) -> None:
    lines = [
        "[Unit]",
        f"Description=REPOS stack {container_name}",
        "",
        "[Container]",
        f"ContainerName={container_name}",
        f"HostName={hostname}",
        f"Image={image_tag}",
        f"Network={network}",
        f"EnvironmentFile={env_file}",
    ]
    if network == "host":
        for mapping in publish_ports:
            lines.append(f"# PublishPort={mapping}")
    else:
        for mapping in publish_ports:
            lines.append(f"PublishPort={mapping}")
    for p in persistent_paths:
        lines.append(f"Volume={container_name}_{volume_suffix(p)}:{p}:Z")
    lines.extend(["", "[Service]", "Restart=always", "RestartSec=3", "", "[Install]", "WantedBy=default.target", ""])
    path.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Config saver
# ---------------------------------------------------------------------------

def save_stack_config(
    path: Path, *, base: BaseConfig, modules: ModuleSelection,
    env: EnvConfig, workspace: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected_array = ", ".join(json.dumps(x) for x in modules.selected)
    forced_array = ", ".join(json.dumps(x) for x in modules.forced)
    publish_array = ", ".join(json.dumps(x) for x in env.publish_ports)
    persistence_array = ", ".join(json.dumps(x) for x in env.persistence_paths)
    def _toml_str(v: str) -> str:
        return json.dumps(v)  # json string encoding is valid TOML basic string
    env_lines = "\n".join([f'{k} = {_toml_str(v)}' for k, v in env.env_values.items()])

    text = f"""schema_version = 1

selected_modules = [{selected_array}]
forced_modules = [{forced_array}]
publish_ports = [{publish_array}]

[meta]
stack = "{base.stack}"
container_name = "{base.container_name}"
hostname = "{base.hostname}"
image_tag = "{base.image_tag}"
network = "{base.network}"
container_prefix = "{base.container_prefix}"
image_registry = "{base.image_registry}"
workspace = "{workspace}"
litellm_required = {"true" if env.litellm_required else "false"}
litellm_mode = "{env.litellm_mode}"
litellm_base_url = {json.dumps(env.env_values.get("OPENAI_API_BASE", ""))}
litellm_local_port = {env.litellm_local_port}

[env]
{env_lines}

[persistence]
paths = [{persistence_array}]
"""
    path.write_text(text)
    print(f"\n[ok] config written:\n- {path}")


# ---------------------------------------------------------------------------
# Main build generation
# ---------------------------------------------------------------------------

def generate_all(
    base: BaseConfig,
    modules: ModuleSelection,
    env: EnvConfig,
    *,
    engine: str = "auto",
    workspace: Path | None = None,
    base_tag: str = "localhost/repos-base:latest",
    depth: int = 1,
    update: bool = False,
    generate_only: bool = False,
    dry_run: bool = False,
    hook_results: list[HookResult] | None = None,
) -> int:
    engine = choose_engine_safe(engine) if generate_only else choose_engine(engine)
    workspace = workspace or ROOT.parent
    hook_results = hook_results or []
    by_name = modules.modules
    selected_mods = [by_name[n] for n in modules.selected if n in by_name]

    # --- Clone/update repos ---
    repo_paths: dict[str, Path] = {}
    for mod in selected_mods:
        if mod.kind != "repo" or not mod.source or not mod.target_dir:
            continue
        repo_paths[mod.name] = ensure_repo(mod, workspace, depth=depth, update=update, dry_run=dry_run)

    # --- Base module / shared base ---
    base_candidates = [mod for mod in selected_mods if mod.is_base]
    base_mod = base_candidates[0] if base_candidates else None

    if base_mod:
        base_repo = repo_paths[base_mod.name]
        base_dockerfile = base_repo / base_mod.dockerfile
        if not base_dockerfile.exists():
            raise RuntimeError(f"Missing base dockerfile: {base_dockerfile}")
    else:
        base_repo = None
        base_dockerfile = None

    use_shared_base = not base_mod and base_image_exists(engine, base_tag)
    if not use_shared_base and not base_mod:
        base_tag = base.base_image

    # --- Output dirs ---
    gen_dir = GENERATED_ROOT / base.stack
    sup_dir = gen_dir / "supervisord"
    gen_dir.mkdir(parents=True, exist_ok=True)
    sup_dir.mkdir(parents=True, exist_ok=True)

    overlay = gen_dir / f"{base.stack}.overlay.Dockerfile"
    run_script = gen_dir / f"{base.stack}_run.sh"
    build_script = gen_dir / f"{base.stack}_build.sh"
    env_file = gen_dir / f"{base.stack}.env"
    container_file = gen_dir / f"{base.stack}.container"

    if use_shared_base:
        print(f"[info] shared base image found: {base_tag}")
    elif not generate_only and base_mod:
        run_cmd([engine, "build", "-f", str(base_dockerfile), "-t", base_tag, str(base_repo)], dry_run=dry_run)

    print(f"[info] stack: {base.stack}")
    print(f"[info] container: {base.container_name}")
    print(f"[info] image: {base.image_tag}")
    print(f"[info] network: {base.network}")
    print(f"[info] engine: {engine}")

    # --- Dockerfile ---
    docker_lines: list[str] = [f"FROM {base_tag}", ""]

    # Package install (skip if shared base)
    if not use_shared_base:
        dnf: list[str] = []
        pip: list[str] = []
        npm: list[str] = []
        for mod in selected_mods:
            if mod.name == "litellm" and env.litellm_mode != "local":
                continue
            for pkg in mod.dnf_requirements:
                if pkg not in dnf:
                    dnf.append(pkg)
            for pkg in mod.pip_requirements:
                if pkg not in pip:
                    pip.append(pkg)
            for pkg in mod.npm_global_requirements:
                if pkg not in npm:
                    npm.append(pkg)
        for pkg in base.base_requirements:
            if pkg not in dnf:
                dnf.insert(0, pkg)
        if pip and "python3-pip" not in dnf:
            dnf.append("python3-pip")
        if dnf:
            docker_lines.append(f"RUN dnf install -y {' '.join(shlex.quote(p) for p in dnf)} && dnf clean all")
        else:
            docker_lines.append("RUN dnf install -y supervisor && dnf clean all")
        docker_lines.append("RUN mkdir -p /etc/supervisor/conf.d /etc/supervisor/conf.d/disabled")
        if pip:
            docker_lines.append(f"RUN python3 -m pip install --no-cache-dir {' '.join(shlex.quote(p) for p in pip)}")
        if npm:
            docker_lines.append(f"RUN npm install -g {' '.join(shlex.quote(p) for p in npm)}")

    # LiteLLM supervisor (local mode)
    if env.litellm_required and env.litellm_mode == "local":
        conf_name = "zz-module-litellm.conf"
        conf_path = sup_dir / conf_name
        write_supervisor_conf(conf_path, [RuntimeProgram(
            name="litellm", command=f"litellm --host 0.0.0.0 --port {env.litellm_local_port}",
            directory="/opt", autostart=True, autorestart=True, startsecs=2, priority=160,
        )])
        docker_lines.append(f"COPY REPOS/generated/{base.stack}/supervisord/{conf_name} {supervisor_target_dir('litellm')}/{conf_name}")

    # Shared python_header.py (env bootstrap for all programs)
    header_src = workspace / "SCRIPTS" / "python_header.py"
    if header_src.exists():
        header_rel = str(header_src.relative_to(workspace))
        docker_lines.append(f"COPY {header_rel} /opt/python_header.py")
        docker_lines.append("RUN python3 -m pip install --no-cache-dir python-dotenv")

    # Module layers
    for mod in selected_mods:
        if mod.kind == "repo":
            if base_mod and mod.name == base_mod.name:
                continue
            repo = repo_paths[mod.name]
            repo_rel = str(repo.relative_to(workspace))
            docker_lines.append(f"COPY {repo_rel} /opt/{mod.target_dir}")
            # Remove symlink first, then copy real python_header.py (symlinks break in containers)
            if header_src.exists():
                docker_lines.append(f"RUN rm -f /opt/{mod.target_dir}/python_header.py")
                docker_lines.append(f"COPY {header_rel} /opt/{mod.target_dir}/python_header.py")
            docker_lines.append(
                f"RUN if [ -f /opt/{mod.target_dir}/requirements.txt ]; then python3 -m pip install --no-cache-dir -r /opt/{mod.target_dir}/requirements.txt; fi"
            )
            if mod.run_setup_py:
                docker_lines.append(
                    f"RUN if [ -f /opt/{mod.target_dir}/setup.py ]; then cd /opt/{mod.target_dir} && python3 setup.py; fi"
                )
            # Deploy scripts: copy deploy/*.sh to /usr/local/bin/ and make executable
            deploy_dir = repo / "deploy"
            if deploy_dir.is_dir():
                for sh in sorted(deploy_dir.glob("*.sh")):
                    sh_rel = str(sh.relative_to(workspace))
                    docker_lines.append(f"COPY {sh_rel} /usr/local/bin/{sh.name}")
                    docker_lines.append(f"RUN chmod +x /usr/local/bin/{sh.name}")
            # Create /run/php-fpm if php-fpm is referenced
            if (repo / "deploy" / "supervisor").is_dir():
                for sc in (repo / "deploy" / "supervisor").iterdir():
                    if sc.suffix == ".conf" and sc.read_text().find("php-fpm") >= 0:
                        docker_lines.append("RUN mkdir -p /run/php-fpm")
                        break
            # Create venvs for subdirs that have requirements.txt
            for subdir in sorted(repo.iterdir()):
                if subdir.is_dir() and (subdir / "requirements.txt").exists():
                    rel = subdir.name
                    docker_lines.append(
                        f"RUN python3 -m venv /opt/{mod.target_dir}/{rel}/venv && "
                        f"/opt/{mod.target_dir}/{rel}/venv/bin/pip install --no-cache-dir "
                        f"-r /opt/{mod.target_dir}/{rel}/requirements.txt"
                    )
            # Module setup script: run on host at configure time with env vars
            # Script generates files into <repo>/generated/ which get COPY'd
            setup_script = repo / "setup_extensions.py"
            if setup_script.exists() and not dry_run:
                setup_env = os.environ.copy()
                setup_env.update(env.env_values)
                gen_out = repo / "generated"
                gen_out.mkdir(exist_ok=True)
                setup_env["CITADEL_GENERATE_DIR"] = str(gen_out)
                subprocess.run(
                    [sys.executable, str(setup_script), "--generate"],
                    cwd=str(repo), env=setup_env, check=True,
                )
                # COPY generated files into container
                for gf in sorted(gen_out.iterdir()):
                    gf_rel = str(gf.relative_to(workspace))
                    if gf.name == "Caddyfile":
                        docker_lines.append(f"COPY {gf_rel} /etc/caddy/Caddyfile")
                    else:
                        docker_lines.append(f"COPY {gf_rel} /opt/{mod.target_dir}/{gf.name}")

            # Supervisor conf
            runtime_file = resolve_ref_path(mod, repo, mod.runtime_ref) or Path("/nonexistent")
            conf_name = f"zz-module-{sanitize_slug(mod.name)}.conf"
            conf_path = sup_dir / conf_name
            if runtime_file.exists() and runtime_file.suffix.lower() == ".conf":
                if not dry_run:
                    shutil.copy2(runtime_file, conf_path)
            else:
                programs = parse_runtime_programs(runtime_file, mod.name, mod.target_dir)
                write_supervisor_conf(conf_path, programs)

            target = supervisor_target_dir(mod.name)
            docker_lines.append(f"COPY REPOS/generated/{base.stack}/supervisord/{conf_name} {target}/{conf_name}")

            # Module/runtime refs
            module_ref_path = resolve_ref_path(mod, repo, mod.module_ref)
            if module_ref_path and module_ref_path.exists() and workspace in module_ref_path.parents:
                rel = str(module_ref_path.relative_to(workspace))
                docker_lines.append(f"RUN mkdir -p /opt/repos/extensions/modules/{sanitize_slug(mod.name)}")
                docker_lines.append(f"COPY {rel} /opt/repos/extensions/modules/{sanitize_slug(mod.name)}/module.toml")

            runtime_ref_path = resolve_ref_path(mod, repo, mod.runtime_ref)
            if runtime_ref_path and runtime_ref_path.exists() and workspace in runtime_ref_path.parents:
                rel = str(runtime_ref_path.relative_to(workspace))
                docker_lines.append(f"COPY {rel} /opt/repos/extensions/modules/{sanitize_slug(mod.name)}/runtime.toml")

        elif mod.kind == "directive":
            if not mod.thirdparty_dir:
                continue
            src = resolve_thirdparty_source(mod.thirdparty_dir, workspace)
            if not src or not src.exists():
                print(f"[warn] missing 3rd-party source: {mod.name}: {mod.thirdparty_dir}")
                continue
            vendor = gen_dir / "vendor" / "3RDPARTY" / sanitize_slug(mod.name)
            if not dry_run:
                if vendor.exists():
                    shutil.rmtree(vendor)
                vendor.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, vendor)
            docker_lines.append("RUN mkdir -p /root")
            docker_lines.append(f"COPY {str(vendor.relative_to(workspace))} /root/{mod.name}")

    # Non-repo runtime confs
    for mod in selected_mods:
        if mod.kind == "repo":
            continue
        runtime_file = resolve_ref_path(mod, workspace, mod.runtime_ref) or Path("/nonexistent")
        if not runtime_file.exists():
            continue
        conf_name = f"zz-module-{sanitize_slug(mod.name)}.conf"
        conf_path = sup_dir / conf_name
        if runtime_file.suffix.lower() == ".conf":
            if not dry_run:
                shutil.copy2(runtime_file, conf_path)
        else:
            programs = parse_runtime_programs(runtime_file, mod.name, mod.target_dir or mod.name)
            write_supervisor_conf(conf_path, programs)
        target = supervisor_target_dir(mod.name)
        docker_lines.append(f"COPY REPOS/generated/{base.stack}/supervisord/{conf_name} {target}/{conf_name}")

    # Apply hook results
    for hr in hook_results:
        for line in hr.dockerfile_lines:
            docker_lines.append(line)
        for k, v in hr.env_additions.items():
            env.env_values[k] = v

    # Entrypoint + supervisord
    supervisord_conf = gen_dir / "supervisord.conf"
    entrypoint_script = gen_dir / "entrypoint.sh"
    if not dry_run:
        supervisord_conf.write_text(
            "[unix_http_server]\nfile=/tmp/supervisor.sock\n\n"
            "[supervisord]\nnodaemon=true\nlogfile=/dev/stdout\nlogfile_maxbytes=0\n"
            "pidfile=/tmp/supervisord.pid\n\n"
            "[rpcinterface:supervisor]\nsupervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface\n\n"
            "[supervisorctl]\nserverurl=unix:///tmp/supervisor.sock\n\n"
            "[include]\nfiles = /etc/supervisor/conf.d/*.conf\n"
        )
        entrypoint_lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "mkdir -p /etc/supervisor/conf.d",
        ]
        for hr in hook_results:
            entrypoint_lines.extend(hr.entrypoint_lines)
        entrypoint_lines.append('exec /usr/bin/supervisord -c /etc/supervisord.conf -n')
        entrypoint_script.write_text("\n".join(entrypoint_lines) + "\n")
        entrypoint_script.chmod(0o755)

    docker_lines.append(f"COPY REPOS/generated/{base.stack}/supervisord.conf /etc/supervisord.conf")
    docker_lines.append(f"COPY REPOS/generated/{base.stack}/entrypoint.sh /entrypoint.sh")
    docker_lines.append('ENTRYPOINT ["/entrypoint.sh"]')
    docker_lines.append("")
    overlay.write_text("\n".join(docker_lines))

    # --- Build image ---
    if not generate_only:
        run_cmd([engine, "build", "-f", str(overlay), "-t", base.image_tag, str(workspace)], dry_run=dry_run)

    # --- Write all scripts ---
    write_run_script(run_script, engine=engine, image_tag=base.image_tag, container_name=base.container_name,
                     hostname=base.hostname, network=base.network, publish_ports=env.publish_ports,
                     env_file=env_file, persistent_paths=env.persistence_paths)
    write_build_script(build_script, engine=engine, base_tag=base_tag, image_tag=base.image_tag,
                       base_dockerfile=base_dockerfile, base_repo=base_repo, overlay=overlay,
                       workspace=workspace, use_shared_base=use_shared_base)
    write_env_file(env_file, env.env_values)
    write_container_file(container_file, image_tag=base.image_tag, container_name=base.container_name,
                         hostname=base.hostname, network=base.network, env_file=env_file,
                         publish_ports=env.publish_ports, persistent_paths=env.persistence_paths)

    if not dry_run:
        run_cmd(["chmod", "+x", str(run_script)])
        run_cmd(["chmod", "+x", str(build_script)])

    # --- Fly.io artifacts ---
    fly_files: list[Path] = []
    if not dry_run:
        fly_files = generate_fly_artifacts(
            stack=base.stack, base=base, selected_mods=selected_mods,
            overlay_path=overlay, env_values=dict(env.env_values),
            publish_ports=env.publish_ports, gen_dir=gen_dir, workspace=workspace,
        )

    # --- Meta ---
    summary = {
        "stack": base.stack, "container_name": base.container_name, "hostname": base.hostname,
        "image": base.image_tag, "network": base.network, "base": base_mod.name if base_mod else base_tag,
        "selected": modules.selected, "persistent_paths": env.persistence_paths,
        "publish_ports": env.publish_ports, "litellm_mode": env.litellm_mode,
        "tailscale": env.tailscale_enabled,
    }
    (gen_dir / "meta.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(f"\n[ok] generated:")
    for f in [overlay, build_script, run_script, env_file, container_file, *fly_files]:
        print(f"- {f}")
    return 0


# ---------------------------------------------------------------------------
# Build base image (standalone)
# ---------------------------------------------------------------------------

def build_base_image(engine: str, base_tag: str, *, base: BaseConfig, dry_run: bool) -> int:
    from config_modules import load_modules as _load_modules
    modules = _load_modules()

    dnf: list[str] = []
    pip: list[str] = []
    npm: list[str] = []
    for mod in modules:
        for pkg in mod.dnf_requirements:
            if pkg not in dnf:
                dnf.append(pkg)
        for pkg in mod.pip_requirements:
            if pkg not in pip:
                pip.append(pkg)
        for pkg in mod.npm_global_requirements:
            if pkg not in npm:
                npm.append(pkg)

    for pkg in base.base_requirements:
        if pkg not in dnf:
            dnf.insert(0, pkg)

    docker_lines = [f"FROM {base.base_image}", ""]
    docker_lines.append(f"RUN dnf install -y {' '.join(shlex.quote(p) for p in dnf)} && dnf clean all")
    docker_lines.append("RUN mkdir -p /etc/supervisor/conf.d /etc/supervisor/conf.d/disabled")
    if pip:
        docker_lines.append(f"RUN python3 -m pip install --no-cache-dir {' '.join(shlex.quote(p) for p in pip)}")
    if npm:
        docker_lines.append(f"RUN npm install -g {' '.join(shlex.quote(p) for p in npm)}")
    docker_lines.append("")

    base_dir = GENERATED_ROOT / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    dockerfile = base_dir / "repos-base.Dockerfile"
    dockerfile.write_text("\n".join(docker_lines))

    print(f"[base] image: {base.base_image}")
    print(f"[base] tag: {base_tag}")
    print(f"[base] dnf: {', '.join(dnf)}")
    if pip:
        print(f"[base] pip: {', '.join(pip)}")

    if not dry_run:
        run_cmd([engine, "build", "-f", str(dockerfile), "-t", base_tag, str(ROOT)], dry_run=dry_run)

    print(f"\n[ok] base image built: {base_tag}")
    return 0
