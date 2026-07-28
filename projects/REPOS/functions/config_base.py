"""Step 1: Base configuration — distro, naming, container, network."""

from __future__ import annotations

import dataclasses
import random
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
CONFIG_BASE_TOML = ROOT / "config_base.toml"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class BaseDefaults:
    """Raw defaults loaded from config_base.toml."""
    base_image: str
    base_requirements: list[str]
    adjectives: list[str]
    animals: list[str]
    container_prefix: str
    image_registry: str
    network: str
    include_thirdparty: bool
    module_exclude: list[str]
    volume_paths: list[str]


@dataclasses.dataclass
class BaseConfig:
    """Result of the base dialog — passed to subsequent steps."""
    stack: str
    container_name: str
    hostname: str
    image_tag: str
    network: str
    base_image: str
    base_requirements: list[str]
    container_prefix: str
    image_registry: str
    include_thirdparty: bool
    module_exclude: list[str]
    volume_paths: list[str]


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def ask_yes_no(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"{question} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "j", "ja", "1", "true"}


def ask_text(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{question}{suffix}: ").strip()
    return raw or default


def ask_int(question: str, default: int) -> int:
    while True:
        raw = ask_text(question, str(default)).strip()
        try:
            return int(raw)
        except (ValueError, TypeError):
            print("Bitte eine Zahl eingeben.")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def suggest_codename(defaults: BaseDefaults) -> str:
    adj = defaults.adjectives or ["steady"]
    ani = defaults.animals or ["fox"]
    return f"{random.choice(adj)}-{random.choice(ani)}"


def normalize_stack(value: str, defaults: BaseDefaults) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    return cleaned or suggest_codename(defaults)


def normalize_container_name(value: str, fallback: str, *, prefix: str) -> str:
    cleaned = value.strip().lower().replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", cleaned).strip("-._")
    if not cleaned:
        cleaned = fallback
    if not cleaned.startswith(prefix):
        cleaned = f"{prefix}{cleaned}"
    return cleaned


def normalize_hostname(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    return cleaned or fallback


def normalize_image_tag(value: str, fallback: str, *, registry: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        raw = fallback
    if "/" in raw:
        return raw
    return f"{registry}/{raw}"


def strip_registry_prefix(image_name: str, *, registry: str) -> str:
    marker = f"{registry}/"
    if image_name.startswith(marker):
        return image_name[len(marker):]
    return image_name


# ---------------------------------------------------------------------------
# Load config_base.toml
# ---------------------------------------------------------------------------

def load_base_defaults(path: Path | None = None) -> BaseDefaults:
    toml_path = path or CONFIG_BASE_TOML
    if not toml_path.exists():
        raise RuntimeError(f"Missing {toml_path}")
    data = tomllib.loads(toml_path.read_text())

    base = data.get("base", {})
    naming = data.get("naming", {})
    container = data.get("container", {})
    modules = data.get("modules", {})
    volumes = data.get("volumes", {})

    exclude_raw = modules.get("exclude", [])
    if isinstance(exclude_raw, str):
        exclude_raw = [exclude_raw]

    vol_raw = volumes.get("paths", [])
    if isinstance(vol_raw, str):
        vol_raw = [vol_raw]

    return BaseDefaults(
        base_image=str(base.get("image", "quay.io/fedora/fedora:43")).strip(),
        base_requirements=[str(x).strip() for x in base.get("requirements", []) if str(x).strip()],
        adjectives=[str(x).strip() for x in naming.get("adjectives", ["steady"])],
        animals=[str(x).strip() for x in naming.get("animals", ["fox"])],
        container_prefix=str(container.get("prefix", "repos-")).strip(),
        image_registry=str(container.get("registry", "localhost")).strip().lower().strip("/"),
        network=str(container.get("network", "host")).strip().lower(),
        include_thirdparty=bool(container.get("include_thirdparty", True)),
        module_exclude=[str(x).strip() for x in exclude_raw if str(x).strip()],
        volume_paths=[str(x).strip() for x in vol_raw if str(x).strip()],
    )


# ---------------------------------------------------------------------------
# Interactive dialog
# ---------------------------------------------------------------------------

def run_base_dialog(
    defaults: BaseDefaults | None = None,
    seed: dict | None = None,
) -> BaseConfig:
    """Run the base configuration dialog. Returns a BaseConfig."""

    if defaults is None:
        defaults = load_base_defaults()
    seed = seed or {}

    prefix = str(seed.get("container_prefix", "")).strip().lower() or defaults.container_prefix
    if not prefix.endswith("-"):
        prefix = f"{prefix}-"
    registry = str(seed.get("image_registry", "")).strip().lower().strip("/") or defaults.image_registry

    # Stack codename
    suggested = normalize_stack(seed.get("stack", "") or suggest_codename(defaults), defaults)
    stack_raw = input(f"Stack codename [{suggested}]: ").strip() or suggested
    stack = normalize_stack(stack_raw, defaults)

    # Container name
    container_default = normalize_container_name(
        seed.get("container_name", ""),
        normalize_container_name(stack, stack, prefix=prefix),
        prefix=prefix,
    )
    container_input = input(f"Container name (Enter = {container_default}) [{container_default}]: ").strip()
    container_name = normalize_container_name(container_input, container_default, prefix=prefix)

    # Hostname
    hostname_default = normalize_hostname(seed.get("hostname", ""), container_name)
    hostname_input = input(f"Hostname (Enter = {hostname_default}) [{hostname_default}]: ").strip()
    hostname = normalize_hostname(hostname_input, hostname_default)

    # Image tag
    image_default = normalize_image_tag(seed.get("image_tag", ""), f"{container_name}:latest", registry=registry)
    image_short = strip_registry_prefix(image_default, registry=registry)
    image_input = input(f"Image tag (without {registry}/) [{image_short}]: ").strip()
    image_tag = normalize_image_tag(image_input, image_short, registry=registry)

    # Network mode
    loaded_network = str(seed.get("network", defaults.network) or defaults.network).strip()
    if loaded_network.lower() == "host":
        net_default = "host"
    elif loaded_network.lower() in {"bridge", "podman"}:
        net_default = "bridge"
    elif loaded_network:
        net_default = "bridge"
    else:
        net_default = defaults.network if defaults.network in {"host", "bridge"} else "host"

    while True:
        network_mode = ask_text("Network mode (host/bridge/custom)", net_default).strip().lower()
        if network_mode in {"host", "bridge", "custom"}:
            break
        print("Bitte host, bridge oder custom eingeben.")

    if network_mode == "host":
        network = "host"
    elif network_mode == "bridge":
        if loaded_network and loaded_network.lower() not in {"host", "bridge", "podman"}:
            bridge_default = loaded_network
        else:
            bridge_default = f"{container_name}-net"
        network = ask_text("Bridge network name", bridge_default).strip() or bridge_default
    else:
        custom_default = loaded_network if loaded_network else f"{container_name}-net"
        network = ask_text("Custom network value (--network)", custom_default).strip() or custom_default

    # Summary
    print(f"[base] stack: {stack}")
    print(f"[base] container: {container_name}")
    print(f"[base] hostname: {hostname}")
    print(f"[base] image: {image_tag}")
    print(f"[base] network: {network}")

    return BaseConfig(
        stack=stack,
        container_name=container_name,
        hostname=hostname,
        image_tag=image_tag,
        network=network,
        base_image=defaults.base_image,
        base_requirements=list(defaults.base_requirements),
        container_prefix=prefix,
        image_registry=registry,
        include_thirdparty=defaults.include_thirdparty,
        module_exclude=list(defaults.module_exclude),
        volume_paths=list(defaults.volume_paths),
    )
