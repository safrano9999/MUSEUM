"""Step 2: Module selection — which programs go into the stack."""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from config_base import BaseConfig, ask_yes_no

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
MODULES_ROOT = ROOT / "MODULES"
WORKSPACE = ROOT.parent
GROUPS = ["PUBLIC", "PRIVATE", "3RDPARTY", "3RDPARTY_DEPENDENCIES"]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class EnvPrompt:
    key: str
    default: str
    description: str
    required: bool = False
    when_litellm_mode: str = ""
    when_network: str = ""
    when_selected: set[str] = dataclasses.field(default_factory=set)
    when_env_key: str = ""
    when_env_values: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class ModuleDef:
    file: Path
    module_dir: Path
    name: str
    group: str
    kind: str
    source: str
    target_dir: str
    description: str
    default_selected: bool
    is_base: bool
    dockerfile: str
    runtime_ref: str
    dependencies: list[str]
    thirdparty_dir: str
    exclude_network: list[str]
    # requirements
    pip_requirements: list[str]
    dnf_requirements: list[str]
    npm_global_requirements: list[str]
    run_setup_py: bool
    # prompts & volumes
    port_prompts: list[tuple[str, int, bool]]
    env_prompts: list[EnvPrompt]
    volume_defaults: dict[str, bool]
    # persistence
    persistence: list[str]
    # integration refs
    module_ref: str


@dataclasses.dataclass
class ModuleSelection:
    """Result of module selection — passed to subsequent steps."""
    selected: list[str]
    explicit: list[str]
    forced: list[str]
    modules: dict[str, ModuleDef]
    all_modules: list[ModuleDef]


# ---------------------------------------------------------------------------
# TOML parsing helpers
# ---------------------------------------------------------------------------

def _parse_exclude_network(module: dict) -> list[str]:
    raw = module.get("exclude_network", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(x).strip().lower() for x in raw if str(x).strip()]


def _env_entry_to_prompt(item: dict) -> EnvPrompt | None:
    """Build an EnvPrompt from a TOML entry dict (used by both formats)."""
    key = str(item.get("key", "")).strip()
    if not key:
        return None
    when_selected_raw = item.get("when_selected", [])
    if isinstance(when_selected_raw, str):
        when_selected_raw = [when_selected_raw]
    when_env_values_raw = item.get("when_env_values", [])
    if isinstance(when_env_values_raw, str):
        when_env_values_raw = [when_env_values_raw]
    return EnvPrompt(
        key=key,
        default=str(item.get("default", "")).strip(),
        description=str(item.get("description", key)).strip(),
        required=bool(item.get("required", False)),
        when_litellm_mode=str(item.get("when_litellm_mode", "")).strip().lower(),
        when_network=str(item.get("when_network", "")).strip().lower(),
        when_selected={str(x).strip() for x in when_selected_raw if str(x).strip()},
        when_env_key=str(item.get("when_env_key", "")).strip(),
        when_env_values={str(x).strip() for x in when_env_values_raw if str(x).strip()},
    )


def _parse_env_prompts(path: Path) -> list[EnvPrompt]:
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text())
    env_root = data.get("env", data) if isinstance(data, dict) else {}
    if not isinstance(env_root, dict):
        return []
    out: list[EnvPrompt] = []
    for item in env_root.get("entries", []):
        if not isinstance(item, dict):
            continue
        prompt = _env_entry_to_prompt(item)
        if prompt:
            out.append(prompt)
    return out


def _parse_repo_fat_module(fat_path: Path) -> tuple[list[EnvPrompt], list[tuple[str, int, bool]], list[str], str, str]:
    """Parse <repo>/CONTAINER/module.toml with [[env]] and [[ports]] inline arrays.

    Returns (env_prompts, port_prompts, dependencies, runtime_ref, module_ref).
    """
    env_prompts: list[EnvPrompt] = []
    port_prompts: list[tuple[str, int, bool]] = []
    deps: list[str] = []
    runtime_ref = ""
    module_ref = ""

    if not fat_path.exists():
        return env_prompts, port_prompts, deps, runtime_ref, module_ref

    data = tomllib.loads(fat_path.read_text())
    module = data.get("module", {}) if isinstance(data, dict) else {}

    # module-level refs + deps
    runtime_ref = str(module.get("runtime_ref", "")).strip()
    module_ref = str(module.get("module_ref", "")).strip()
    for item in module.get("dependencies", []):
        v = str(item).strip()
        if v and v not in deps:
            deps.append(v)

    # [[ports]] → (env_key, default, publish)
    for p in data.get("ports", []):
        if not isinstance(p, dict):
            continue
        env_key = str(p.get("env_key", "")).strip()
        internal = p.get("internal")
        if not env_key and internal is not None:
            # Derive env key from module name if not set
            env_key = str(p.get("name", "")).strip() or f"PORT_{internal}"
        if not env_key:
            continue
        try:
            default = int(p.get("default", internal or 0))
        except (TypeError, ValueError):
            default = 0
        publish = bool(p.get("publish", p.get("publish_default", True)))
        port_prompts.append((env_key, default, publish))

    # [[env]] → EnvPrompt
    for e in data.get("env", []):
        if not isinstance(e, dict):
            continue
        prompt = _env_entry_to_prompt(e)
        if prompt:
            env_prompts.append(prompt)

    return env_prompts, port_prompts, deps, runtime_ref, module_ref


def _parse_port_prompts(path: Path) -> list[tuple[str, int, bool]]:
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text())
    ports_root = data.get("ports", data) if isinstance(data, dict) else {}
    if not isinstance(ports_root, dict):
        return []
    out: list[tuple[str, int, bool]] = []
    for item in ports_root.get("entries", []):
        if not isinstance(item, dict):
            continue
        env_key = str(item.get("env_key", "")).strip()
        if not env_key:
            continue
        default = int(item.get("default", 0))
        publish = bool(item.get("publish", True))
        out.append((env_key, default, publish))
    return out


def _parse_volume_defaults(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text())
    vol_root = data.get("volumes", data) if isinstance(data, dict) else {}
    if not isinstance(vol_root, dict):
        return {}
    out: dict[str, bool] = {}
    raw_paths = vol_root.get("paths", [])
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    if isinstance(raw_paths, list):
        for item in raw_paths:
            p = str(item).strip()
            if p.startswith("/"):
                out[p] = True
    for item in vol_root.get("entries", []):
        if not isinstance(item, dict):
            continue
        p = str(item.get("path", "")).strip()
        if p.startswith("/"):
            out[p] = bool(item.get("enabled", True))
    return out


def _parse_requirements(path: Path) -> tuple[list[str], list[str], list[str]]:
    if not path.exists():
        return [], [], []
    data = tomllib.loads(path.read_text())
    req = data.get("requirements", data) if isinstance(data, dict) else {}
    if not isinstance(req, dict):
        return [], [], []
    pip = [str(x).strip() for x in req.get("pip", []) if str(x).strip()]
    dnf = [str(x).strip() for x in req.get("dnf", []) if str(x).strip()]
    npm = [str(x).strip() for x in req.get("npm_global", []) if str(x).strip()]
    return dnf, pip, npm


def _parse_dependencies(module: dict, dep_file: Path) -> list[str]:
    deps: list[str] = [str(x).strip() for x in module.get("dependencies", []) if str(x).strip()]
    if dep_file.exists():
        data = tomllib.loads(dep_file.read_text())
        dep_root = data.get("dependencies", data) if isinstance(data, dict) else {}
        raw = dep_root.get("requires", [])
        if isinstance(raw, str):
            raw = [raw]
        for item in raw:
            v = str(item).strip()
            if v and v not in deps:
                deps.append(v)
    return deps


def _parse_persistence(module_data: dict, path: Path) -> list[str]:
    out: list[str] = []
    # From persistence.toml
    pers_file = path / "persistence.toml"
    if pers_file.exists():
        data = tomllib.loads(pers_file.read_text())
        pers_root = data.get("persistence", data) if isinstance(data, dict) else {}
        raw = pers_root.get("paths", [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            for item in raw:
                p = str(item).strip()
                if p.startswith("/") and p not in out:
                    out.append(p)
    # From module.toml persistence section
    for item in module_data.get("persistence", []):
        if isinstance(item, dict):
            p = str(item.get("path", "")).strip()
            if p.startswith("/") and p not in out:
                out.append(p)
    return out


# ---------------------------------------------------------------------------
# Module parsing
# ---------------------------------------------------------------------------

def parse_module_dir(path: Path, group: str) -> ModuleDef:
    module_file = path / "module.toml"
    if not module_file.exists():
        raise RuntimeError(f"Missing module.toml in {path}")

    module_data = tomllib.loads(module_file.read_text())
    module = module_data.get("module", {}) if isinstance(module_data, dict) else {}

    name = str(module.get("name", path.name)).strip()
    kind = str(module.get("kind", "repo")).strip() or "repo"
    target_dir = str(module.get("target_dir", "")).strip()

    # System packages (dnf/pip/npm) stay in REPOS/MODULES/<name>/requirements.toml
    # because base image is built before repos are cloned
    dnf, pip, npm = _parse_requirements(path / "requirements.toml")

    # For repo modules, load env/ports/runtime/deps from the repo's CONTAINER/module.toml (fat format)
    # if the repo is cloned. Falls back to the legacy per-file format in REPOS/MODULES/ otherwise.
    env_prompts: list[EnvPrompt] = []
    port_prompts: list[tuple[str, int, bool]] = []
    repo_deps: list[str] = []
    runtime_ref_from_repo = ""
    module_ref_from_repo = ""
    if kind == "repo" and target_dir:
        repo_fat = WORKSPACE / target_dir / "CONTAINER" / "module.toml"
        if repo_fat.exists():
            env_prompts, port_prompts, repo_deps, runtime_ref_from_repo, module_ref_from_repo = _parse_repo_fat_module(repo_fat)

    # Legacy fallback: per-file format in REPOS/MODULES/<name>/
    if not env_prompts:
        env_prompts = _parse_env_prompts(path / "env.toml")
    if not port_prompts:
        port_prompts = _parse_port_prompts(path / "ports.toml")

    # Integration (legacy)
    integration_file = path / "integration.toml"
    integration: dict = {}
    if integration_file.exists():
        idata = tomllib.loads(integration_file.read_text())
        integration = idata.get("integration", idata) if isinstance(idata, dict) else {}

    runtime_default = "@module/runtime.toml" if (path / "runtime.toml").exists() else "CONTAINER/runtime.toml"
    runtime_ref = (runtime_ref_from_repo
                   or str(integration.get("runtime_ref", module.get("runtime_ref", runtime_default))).strip()
                   or runtime_default)
    module_ref = (module_ref_from_repo
                  or str(integration.get("module_ref", module.get("module_ref", "CONTAINER/module.toml"))).strip()
                  or "CONTAINER/module.toml")

    # Dependencies: merge repo fat + legacy dependencies.toml + module.dependencies
    dependencies = _parse_dependencies(module, path / "dependencies.toml")
    for d in repo_deps:
        if d not in dependencies:
            dependencies.append(d)

    return ModuleDef(
        file=module_file,
        module_dir=path,
        name=name,
        group=group,
        kind=kind,
        source=str(module.get("source", "")).strip(),
        target_dir=target_dir,
        description=str(module.get("description", "")).strip(),
        default_selected=bool(module.get("default_selected", False)),
        is_base=bool(module.get("is_base", False)),
        dockerfile=str(module.get("dockerfile", "Dockerfile")).strip() or "Dockerfile",
        module_ref=module_ref,
        runtime_ref=runtime_ref,
        dependencies=dependencies,
        thirdparty_dir=str(module.get("thirdparty_dir", "")).strip(),
        exclude_network=_parse_exclude_network(module),
        pip_requirements=pip,
        dnf_requirements=dnf,
        npm_global_requirements=npm,
        run_setup_py=bool(module.get("run_setup_py", False)),
        port_prompts=port_prompts,
        env_prompts=env_prompts,
        volume_defaults=_parse_volume_defaults(path / "vol.toml"),
        persistence=_parse_persistence(module_data, path),
    )


def load_modules() -> list[ModuleDef]:
    out: list[ModuleDef] = []
    for group in GROUPS:
        group_dir = MODULES_ROOT / group
        if not group_dir.exists():
            continue
        for path in sorted(group_dir.iterdir()):
            if path.is_dir():
                out.append(parse_module_dir(path, group))
    return out


def module_map(modules: list[ModuleDef]) -> dict[str, ModuleDef]:
    return {m.name: m for m in modules}


# ---------------------------------------------------------------------------
# Dependency resolution
# ---------------------------------------------------------------------------

def apply_dependencies(selected: set[str], by_name: dict[str, ModuleDef]) -> set[str]:
    changed = True
    while changed:
        changed = False
        for name in list(selected):
            mod = by_name.get(name)
            if not mod:
                continue
            for dep in mod.dependencies:
                if dep not in selected and dep in by_name:
                    selected.add(dep)
                    changed = True
    return selected


# ---------------------------------------------------------------------------
# Group exclude helpers
# ---------------------------------------------------------------------------

def _normalize_group_token(token: str) -> str:
    aliases = {
        "3rdparty": "3RDPARTY",
        "third_party": "3RDPARTY",
        "thirdparty": "3RDPARTY",
        "3rdparty_dependencies": "3RDPARTY_DEPENDENCIES",
        "3rdparty_deps": "3RDPARTY_DEPENDENCIES",
        "deps": "3RDPARTY_DEPENDENCIES",
    }
    normalized = token.strip().lower().replace("-", "_")
    return aliases.get(normalized, token.strip().upper())


def load_module_excludes(base: BaseConfig) -> set[str]:
    return {_normalize_group_token(x) for x in base.module_exclude if x.strip()}


# ---------------------------------------------------------------------------
# Interactive dialog
# ---------------------------------------------------------------------------

def run_module_selection(
    base: BaseConfig,
    modules: list[ModuleDef] | None = None,
    seed_selected: set[str] | None = None,
) -> ModuleSelection:
    """Run module selection dialog. Returns ModuleSelection."""

    if modules is None:
        modules = load_modules()
    by_name = module_map(modules)
    seed_selected = seed_selected or set()
    excluded_groups = load_module_excludes(base)

    if excluded_groups:
        print(f"[modules] exclude: {', '.join(sorted(excluded_groups))}")

    selected: set[str] = set()
    explicit: set[str] = set()

    # PUBLIC + PRIVATE
    for group in ("PUBLIC", "PRIVATE"):
        if group in excluded_groups:
            print(f"[skip] group excluded: {group}")
            continue
        group_items = [m for m in modules if m.group == group]
        if not group_items:
            continue
        print(f"\n=== {group} ===")
        for m in group_items:
            if m.exclude_network and base.network in m.exclude_network:
                print(f"[skip] {m.name} excluded for network={base.network}")
                continue

            label = m.target_dir or m.name

            # Bridge mode requires CITADEL (reverse proxy)
            if m.name == "citadel" and base.network not in {"host", ""}:
                print(f"{label} -> {m.description or m.name} [auto: bridge mode requires reverse proxy]")
                selected.add(m.name)
                explicit.add(m.name)
                selected = apply_dependencies(selected, by_name)
                continue

            default_select = (m.name in seed_selected) if seed_selected else m.default_selected
            if ask_yes_no(f"{label} -> {m.description or m.name}", default=default_select):
                before = set(selected)
                selected.add(m.name)
                explicit.add(m.name)
                selected = apply_dependencies(selected, by_name)
                pulled = sorted(x for x in selected if x not in before and x != m.name)
                if pulled:
                    print(f"[auto] {m.name} dependencies: {', '.join(pulled)}")

    selected = apply_dependencies(selected, by_name)

    # 3RDPARTY
    group_3p = [m for m in modules if m.group == "3RDPARTY"]
    if group_3p and "3RDPARTY" not in excluded_groups:
        wants_3p_default = any(m.name in seed_selected for m in group_3p) if seed_selected else base.include_thirdparty
        wants_3p = ask_yes_no("3rd-party integrieren?", default=wants_3p_default)
        if wants_3p:
            print("\n=== 3RDPARTY ===")
            for m in group_3p:
                if m.name in selected:
                    continue
                if m.exclude_network and base.network in m.exclude_network:
                    print(f"[skip] {m.name} excluded for network={base.network}")
                    continue
                default_select = (m.name in seed_selected) if seed_selected else m.default_selected
                if ask_yes_no(f"{m.name} -> {m.description or m.name}", default=default_select):
                    selected.add(m.name)
                    explicit.add(m.name)
    elif "3RDPARTY" in excluded_groups:
        print("[skip] group excluded: 3RDPARTY")

    selected = apply_dependencies(selected, by_name)
    forced = sorted(x for x in selected if x not in explicit)
    for dep in forced:
        print(f"[auto] dependency selected: {dep}")

    return ModuleSelection(
        selected=sorted(selected),
        explicit=sorted(explicit),
        forced=forced,
        modules=by_name,
        all_modules=modules,
    )
