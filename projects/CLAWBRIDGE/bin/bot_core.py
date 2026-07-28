#!/usr/bin/env python3
"""
OPENCLAW — plugin-based Telegram bot core

Auto-discovers openclaw_plugin.json in all sibling project directories (../*/).
Each project opts in by placing an openclaw_plugin.json in its root.
Duplicate command names across plugins → hard error on startup.
/help is a native core command that lists all commands from all plugin files.
Free-text handler is always registered last (plugin sets FREE_TEXT_HANDLER).
"""

import os
import sys
import glob
import json
import time
import hashlib
import importlib.util
import logging
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BASE_DIR     = Path(__file__).resolve().parent.parent

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot_core")

# Load deployment config first (path overrides, no credentials)
load_dotenv(BASE_DIR / "clawbridge.conf")

# Resolve paths — conf can override, otherwise use defaults relative to this file
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", str(BASE_DIR.parent)))
TRIGGERDIR   = Path(os.getenv("TRIGGERDIR",   str(BASE_DIR / "TRIGGERDIR"))) / "rafael"

# Load all credentials from CLAWBRIDGE root (single source of truth)
load_dotenv(BASE_DIR / ".botenv")    # BOT_TOKEN, CHAT_ID
load_dotenv(BASE_DIR / ".env")       # LLM API keys
load_dotenv(BASE_DIR / ".mysqlenv")  # DB credentials

# {cmd: {plugin, description, mode, job, reply_before, plugin_dir}}
COMMAND_REGISTRY: dict = {}


# ── Plugin discovery ───────────────────────────────────────────────────────────

def scan_plugins() -> list:
    """
    Scan ../*/openclaw_plugin.json (all sibling project directories).
    Returns [(project_dir, config), ...] sorted by project name.
    Exits with error if any command name is registered by more than one plugin.
    """
    plugins = []
    errors  = []

    for json_path in sorted(glob.glob(str(PROJECTS_DIR / "*" / "clawbridge_plugin.json"))):
        project_dir = Path(json_path).parent
        with open(json_path) as f:
            config = json.load(f)

        plugin_name = config.get("plugin", project_dir.name)

        for cmd, meta in config.get("commands", {}).items():
            if cmd in COMMAND_REGISTRY:
                errors.append(
                    f"DUPLICATE /{cmd}: claimed by "
                    f"'{COMMAND_REGISTRY[cmd]['plugin']}' and '{plugin_name}'"
                )
            else:
                COMMAND_REGISTRY[cmd] = {
                    "plugin":       plugin_name,
                    "project_dir":  project_dir,
                    "description":  meta.get("description", ""),
                    "mode":         meta.get("mode", "python"),
                    "job":          meta.get("job", ""),
                    "reply_before": meta.get("reply_before", ""),
                }

        plugins.append((project_dir, config))

    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)

    return plugins


# ── Native /help ───────────────────────────────────────────────────────────────

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered commands grouped by plugin."""
    lines = ["*Available commands:*\n"]

    by_plugin: dict = {}
    for cmd, meta in sorted(COMMAND_REGISTRY.items()):
        by_plugin.setdefault(meta["plugin"], []).append(
            (cmd, meta["description"])
        )

    for plugin, cmds in sorted(by_plugin.items()):
        lines.append(f"*{plugin}*")
        for cmd, desc in cmds:
            lines.append(f"  /{cmd} — {desc}")
        lines.append("")

    lines.append("*core*")
    lines.append("  /help — List all available commands")
    lines.append("  /clawbridge — Same as /help")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Generic job handler factory ────────────────────────────────────────────────

def make_job_handler(cmd: str, meta: dict):
    """Return an async handler that drops a command payload to TRIGGERDIR."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        job          = meta["job"]
        reply_before = meta["reply_before"]
        uid          = hashlib.md5(f"{cmd}{time.time()}".encode()).hexdigest()[:8]

        if reply_before:
            await update.message.reply_text(reply_before)

        payload = {
            "type":         "command",
            "job":          job,
            "id":           uid,
            "reply_before": reply_before,
        }
        trigger_file = TRIGGERDIR / f"cmd_{uid}.json"
        with open(trigger_file, "w") as f:
            json.dump(payload, f)

        logger.info(f"[{cmd}] job={job} id={uid} → TRIGGERDIR")

    return handler


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    TRIGGERDIR.mkdir(parents=True, exist_ok=True)

    plugins = scan_plugins()

    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token in ("...", ""):
        logger.error("BOT_TOKEN not set in telegram_actions/.botenv")
        sys.exit(1)

    app = Application.builder().token(token).build()

    # native /help + /clawbridge alias
    app.add_handler(CommandHandler("help",       help_cmd))
    app.add_handler(CommandHandler("clawbridge", help_cmd))

    free_text_handler = None

    for project_dir, config in plugins:
        plugin_name = config.get("plugin", project_dir.name)

        # register job-mode commands
        for cmd, meta in config.get("commands", {}).items():
            if COMMAND_REGISTRY[cmd]["mode"] == "job":
                app.add_handler(
                    CommandHandler(cmd, make_job_handler(cmd, COMMAND_REGISTRY[cmd]))
                )
                logger.info(f"job handler: /{cmd} → {meta.get('job')}")

        # load Python plugin — path from "handler" key, relative to project dir
        handler_rel = config.get("handler", "")
        py_file = (project_dir / handler_rel).resolve() if handler_rel else None
        if py_file and py_file.exists():
            spec = importlib.util.spec_from_file_location(plugin_name, py_file)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # plugins that handle free text expose FREE_TEXT_HANDLER
            if hasattr(mod, "FREE_TEXT_HANDLER"):
                free_text_handler = mod.FREE_TEXT_HANDLER

            if hasattr(mod, "register"):
                mod.register(app)
                logger.info(f"loaded plugin: {plugin_name}")

    # free-text handler MUST be registered last
    if free_text_handler:
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_handler)
        )
        logger.info("registered free-text handler (ai_chat)")

    logger.info(f"bot starting — {len(COMMAND_REGISTRY)} commands + /help")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
