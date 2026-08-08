"""Step 3: Environment configuration — vars, ports, LiteLLM, persistence."""

from __future__ import annotations

import dataclasses
from collections import OrderedDict
from pathlib import Path

from config_base import BaseConfig, ask_yes_no, ask_text, ask_int
from config_modules import ModuleSelection, EnvPrompt

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
MODULES_ROOT = ROOT / "MODULES"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class LiteLLMDefaults:
    modules: set[str]
    default_mode: str
    external_base_url: str
    local_port: int
    default_model: str
    model_candidates: list[str]
    dependency_models: dict[str, list[str]]


@dataclasses.dataclass
class EnvConfig:
    """Result of the environment dialog — passed to config_build."""
    env_values: OrderedDict[str, str]
    publish_ports: list[str]
    persistence_paths: list[str]
    litellm_required: bool
    litellm_mode: str
    litellm_local_port: int
    tailscale_enabled: bool


# ---------------------------------------------------------------------------
# LiteLLM config loading
# ---------------------------------------------------------------------------

def _load_litellm_config() -> LiteLLMDefaults:
    config_path = MODULES_ROOT / "3RDPARTY_DEPENDENCIES" / "litellm" / "config.toml"
    if not config_path.exists():
        return LiteLLMDefaults(
            modules={"napoleon", "jugo", "pvdach"},
            default_mode="external",
            external_base_url="http://127.0.0.1:4000/v1",
            local_port=4000,
            default_model="openai/gpt-5.4",
            model_candidates=["openai/gpt-5.4", "anthropic/claude-sonnet-4", "google/gemini-2.5-pro"],
            dependency_models={},
        )
    data = tomllib.loads(config_path.read_text())
    ll = data.get("litellm", {}) if isinstance(data, dict) else {}

    modules_raw = ll.get("modules", [])
    if isinstance(modules_raw, str):
        modules_raw = [modules_raw]

    dep_models: dict[str, list[str]] = {}
    raw_deps = ll.get("dependency_models", {})
    if isinstance(raw_deps, dict):
        for k, v in raw_deps.items():
            if isinstance(v, list):
                dep_models[str(k).strip().lower()] = [str(x).strip() for x in v if str(x).strip()]

    return LiteLLMDefaults(
        modules={str(x).strip().lower() for x in modules_raw if str(x).strip()},
        default_mode=str(ll.get("default_mode", "external")).strip().lower(),
        external_base_url=str(ll.get("external_base_url", "http://127.0.0.1:4000/v1")).strip(),
        local_port=int(ll.get("local_port", 4000)),
        default_model=str(ll.get("default_model", "openai/gpt-5.4")).strip(),
        model_candidates=[str(x).strip() for x in ll.get("model_candidates", []) if str(x).strip()],
        dependency_models=dep_models,
    )


def _build_model_candidates(ll: LiteLLMDefaults, selected: list[str]) -> list[str]:
    out: list[str] = []
    for name in selected:
        for model in ll.dependency_models.get(name.lower(), []):
            if model not in out:
                out.append(model)
    for model in ll.model_candidates:
        if model not in out:
            out.append(model)
    if ll.default_model and ll.default_model not in out:
        out.insert(0, ll.default_model)
    return out


# ---------------------------------------------------------------------------
# Port publish helper
# ---------------------------------------------------------------------------

def _ask_publish_port(container_port: int, publish_ports: list[str]) -> list[str]:
    """Ask for host port mapping. Returns updated publish_ports list."""
    publish_ports = [p for p in publish_ports if not p.endswith(f":{container_port}") and p != str(container_port)]
    while True:
        pub = ask_text(f"Publish [{container_port}]", str(container_port)).strip()
        if pub.lower() in {"n", "no"}:
            return publish_ports
        host_port = pub if pub else str(container_port)
        if not host_port.isdigit() or not (1 <= int(host_port) <= 65535):
            print(f"Ungültiger Port: {host_port} (1-65535 oder n zum Überspringen)")
            continue
        publish_ports.append(f"{host_port}:{container_port}")
        return publish_ports


# ---------------------------------------------------------------------------
# Env prompt matching
# ---------------------------------------------------------------------------

def _prompt_matches(
    prompt: EnvPrompt,
    *,
    selected: set[str],
    litellm_mode: str,
    network: str,
    env_values: OrderedDict[str, str],
) -> bool:
    if prompt.when_litellm_mode and prompt.when_litellm_mode not in {"any", litellm_mode}:
        return False
    if prompt.when_network and prompt.when_network not in {"any", network}:
        return False
    if prompt.when_selected and not prompt.when_selected & selected:
        return False
    if prompt.when_env_key:
        current = env_values.get(prompt.when_env_key, "").strip().lower()
        if prompt.when_env_values and current not in {v.lower() for v in prompt.when_env_values}:
            return False
    return True


# ---------------------------------------------------------------------------
# Interactive dialog
# ---------------------------------------------------------------------------

def run_env_dialog(
    base: BaseConfig,
    modules: ModuleSelection,
    seed_env: OrderedDict[str, str] | None = None,
    seed_ports: list[str] | None = None,
    seed_persistence: set[str] | None = None,
    seed_meta: dict | None = None,
) -> EnvConfig:
    """Run the environment configuration dialog. Returns EnvConfig."""

    seed_env = seed_env or OrderedDict()
    seed_ports = seed_ports or []
    seed_meta = seed_meta or {}
    by_name = modules.modules
    selected_set = set(modules.selected)
    selected_lower = {x.lower() for x in modules.selected}

    env_values: OrderedDict[str, str] = OrderedDict()
    publish_ports: list[str] = list(seed_ports)

    # --- LiteLLM ---
    ll = _load_litellm_config()
    litellm_required = "litellm" in selected_lower
    llm_apps_selected = litellm_required or any(name in ll.modules for name in selected_lower)
    litellm_mode = str(seed_meta.get("litellm_mode", "")).strip().lower() or ll.default_mode
    if litellm_mode not in {"external", "local"}:
        litellm_mode = ll.default_mode
    try:
        litellm_local_port = int(str(seed_meta.get("litellm_local_port", ll.local_port)).strip() or ll.local_port)
    except (ValueError, TypeError):
        litellm_local_port = ll.local_port
    litellm_base_url = str(seed_meta.get("litellm_base_url", "")).strip() or ll.external_base_url

    if llm_apps_selected:
        mode_default = "sdk" if litellm_mode == "local" else "proxy"
        while True:
            mode_choice = ask_text("LiteLLM backend (sdk/proxy)", mode_default).strip().lower()
            if mode_choice in {"sdk", "proxy"}:
                break
            print("Bitte sdk oder proxy eingeben.")
        litellm_mode = "local" if mode_choice == "sdk" else "external"

        if litellm_mode == "local":
            litellm_local_port = ask_int(
                "LITELLM_LOCAL_PORT",
                int(str(seed_env.get("LITELLM_LOCAL_PORT", litellm_local_port)) or litellm_local_port),
            )
            litellm_base_url = f"http://127.0.0.1:{litellm_local_port}/v1"
            if base.network != "host":
                publish_ports = _ask_publish_port(litellm_local_port, publish_ports)
        else:
            litellm_base_url = ask_text(
                "OPENAI_API_BASE (LiteLLM URL)",
                seed_env.get("OPENAI_API_BASE", litellm_base_url),
            )

        env_values["LITELLM_MODE"] = litellm_mode
        env_values["OPENAI_API_BASE"] = litellm_base_url
        if litellm_mode == "local":
            env_values["LITELLM_LOCAL_PORT"] = str(litellm_local_port)

        # Model candidates
        candidates = _build_model_candidates(ll, modules.selected)
        if candidates:
            print(f"[models] priority: {', '.join(candidates)}")
            default_model = seed_env.get("DEFAULT_MODEL", candidates[0])
            env_values["DEFAULT_MODEL"] = ask_text("DEFAULT_MODEL", default_model)

    # --- Module env prompts ---
    print("\n=== Env ===")
    seen_env: set[str] = set()
    for module_name in modules.selected:
        mod = by_name.get(module_name)
        if not mod:
            continue
        for prompt in mod.env_prompts:
            if prompt.key in seen_env or prompt.key in env_values:
                continue
            if not _prompt_matches(prompt, selected=selected_set, litellm_mode=litellm_mode, network=base.network, env_values=env_values):
                continue
            seen_env.add(prompt.key)
            default_val = seed_env.get(prompt.key, prompt.default)
            while True:
                label = f"{prompt.key} ({prompt.description})" if prompt.description != prompt.key else prompt.key
                value = ask_text(label, default_val)
                if prompt.required and not value.strip():
                    print(f"{prompt.key} ist erforderlich.")
                    continue
                env_values[prompt.key] = value
                break

    # --- Ports ---
    print("\n=== Ports ===")
    seen_ports: set[str] = set()
    for module_name in modules.selected:
        mod = by_name.get(module_name)
        if not mod:
            continue
        for env_key, default_port, publish_default in mod.port_prompts:
            if env_key in seen_ports:
                continue
            seen_ports.add(env_key)
            loaded_raw = seed_env.get(env_key, str(default_port)).strip()
            if not loaded_raw.isdigit():
                loaded_raw = str(default_port)
            service_port = ask_int(env_key, int(loaded_raw))
            env_values[env_key] = str(service_port)

            if base.network != "host":
                publish_ports = _ask_publish_port(service_port, publish_ports)

    publish_ports = sorted(set(publish_ports))

    # --- Persistence ---
    persistence_paths: list[str] = list(seed_persistence) if seed_persistence else list(base.volume_paths)

    # Collect from modules
    for module_name in modules.selected:
        mod = by_name.get(module_name)
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

    # --- Tailscale & runtime vars ---
    tailscale_enabled = "tailscale" in selected_lower
    env_values["CITADEL_ENABLE_TAILSCALE"] = "1" if tailscale_enabled else "0"
    env_values["TS_HOSTNAME"] = base.hostname

    return EnvConfig(
        env_values=env_values,
        publish_ports=publish_ports,
        persistence_paths=persistence_paths,
        litellm_required=litellm_required,
        litellm_mode=litellm_mode,
        litellm_local_port=litellm_local_port,
        tailscale_enabled=tailscale_enabled,
    )
