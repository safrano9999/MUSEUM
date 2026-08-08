"""
ai_chat plugin — multi-provider LLM chat via litellm

Feature env files (copy example → dotfile, fill keys):
  webenv.example   → .webenv   — web search  (Brave, Tavily, SerpAPI, Serper)
  imageenv.example → .imageenv — image gen   (DALL-E, Stability, Replicate, fal.ai)
  voiceenv.example → .voiceenv — voice/TTS   (Whisper, Gemini, ElevenLabs, OpenAI TTS)

Exposes: register(app), FREE_TEXT_HANDLER
"""

import os
import io
import re as _re
import base64
import json
import time
import asyncio
import functools
import concurrent.futures
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import litellm

logger = logging.getLogger("ai_chat")

PLUGIN_DIR        = Path(__file__).parent
CONVERSATIONS_DIR = PLUGIN_DIR / "conversations"
CURRENT_CONV_FILE = PLUGIN_DIR / "current_conversation.json"
FAVORITES_FILE    = PLUGIN_DIR / "favorites.json"

MODELS_PER_PAGE = 30
LLM_TIMEOUT     = 120

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


# ── Env file loader helper ─────────────────────────────────────────────────────

def _load_dotenv(filename: str):
    """Load .filename from own dir first, then CLAWBRIDGE boss dir."""
    own  = PLUGIN_DIR / filename
    boss = PLUGIN_DIR.parent / "CLAWBRIDGE" / filename
    if own.exists():
        load_dotenv(own, override=False)
    elif boss.exists():
        load_dotenv(boss, override=False)


_load_dotenv(".webenv")
_load_dotenv(".imageenv")
_load_dotenv(".voiceenv")
_load_dotenv("host.conf")

# ── Search registry ────────────────────────────────────────────────────────────

_SEARCH_KEY_MAP = {
    "BRAVE_API_KEY":  "brave",
    "TAVILY_API_KEY": "tavily",
    "SERPAPI_KEY":    "serpapi",
    "SERPER_API_KEY": "serper",
}


def build_search_registry() -> Dict[str, str]:
    registry = {"duckduckgo": ""}
    for env_key, provider in _SEARCH_KEY_MAP.items():
        val = os.getenv(env_key, "")
        if val and val not in ("...", ""):
            registry[provider] = val
    return registry


SEARCH_REGISTRY: Dict[str, str] = build_search_registry()
logger.info(f"Search providers: {list(SEARCH_REGISTRY.keys())}")

# ── Image registry ─────────────────────────────────────────────────────────────

_IMAGE_KEY_MAP = {
    "DALLE_API_KEY":     "dalle",
    "STABILITY_API_KEY": "stability",
    "REPLICATE_API_KEY": "replicate",
    "FAL_API_KEY":       "fal",
}


def build_image_registry() -> Dict[str, str]:
    registry = {}
    for env_key, provider in _IMAGE_KEY_MAP.items():
        val = os.getenv(env_key, "")
        if val and val not in ("...", ""):
            registry[provider] = val
    return registry


IMAGE_REGISTRY: Dict[str, str] = build_image_registry()
logger.info(f"Image providers: {list(IMAGE_REGISTRY.keys())}")

# ── Video registry ─────────────────────────────────────────────────────────────

_VIDEO_KEY_MAP = {
    "REPLICATE_API_KEY": "replicate",
    "FAL_API_KEY":       "fal",
}


def build_video_registry() -> Dict[str, str]:
    registry = {}
    for env_key, provider in _VIDEO_KEY_MAP.items():
        val = os.getenv(env_key, "")
        if val and val not in ("...", ""):
            registry[provider] = val
    return registry


VIDEO_REGISTRY: Dict[str, str] = build_video_registry()
logger.info(f"Video providers: {list(VIDEO_REGISTRY.keys())}")

# ── Voice / TTS registries ─────────────────────────────────────────────────────

_TRANSCRIPTION_KEY_MAP = {
    "WHISPER_API_KEY":  "whisper",
    "GEMINI_VOICE_KEY": "gemini",
}

_TTS_KEY_MAP = {
    "ELEVENLABS_API_KEY": "elevenlabs",
    "OPENAI_TTS_KEY":     "openai_tts",
}


def build_transcription_registry() -> Dict[str, str]:
    registry = {}
    for env_key, provider in _TRANSCRIPTION_KEY_MAP.items():
        val = os.getenv(env_key, "")
        if val and val not in ("...", ""):
            registry[provider] = val
    return registry


def build_tts_registry() -> Dict[str, str]:
    registry = {}
    for env_key, provider in _TTS_KEY_MAP.items():
        val = os.getenv(env_key, "")
        if val and val not in ("...", ""):
            registry[provider] = val
    return registry


TRANSCRIPTION_REGISTRY: Dict[str, str] = build_transcription_registry()
TTS_REGISTRY:           Dict[str, str] = build_tts_registry()
logger.info(f"Transcription providers: {list(TRANSCRIPTION_REGISTRY.keys())}")
logger.info(f"TTS providers: {list(TTS_REGISTRY.keys())}")

# ── Tool definitions ───────────────────────────────────────────────────────────

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current, real-time information. "
            "Use this when the question requires up-to-date data, recent events, "
            "live prices, news, or anything that may have changed after your training cutoff."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query string"}
            },
            "required": ["query"],
        },
    },
}

IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Generate an image from a text description. "
            "Use when the user asks for an image, picture, illustration, photo, or any visual content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Detailed description of the image to generate"}
            },
            "required": ["prompt"],
        },
    },
}

DOCUMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_document",
        "description": (
            "Generate a file and send it to the user. "
            "Use when the user asks for a downloadable file, document, or attachment. "
            "Supported formats: .ics (calendar events), .md (markdown), .txt (plain text), .csv, .json, .html. "
            "For calendar events (appointments, meetings, reminders) always use .ics format with valid iCalendar content. "
            "For notes, lists, or structured text use .md or .txt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename with extension, e.g. 'termin.ics', 'einkaufsliste.md'"},
                "content":  {"type": "string", "description": "Full file content as a string"},
            },
            "required": ["filename", "content"],
        },
    },
}

# ── Search adapters ────────────────────────────────────────────────────────────

def _search_sync(provider: str, query: str) -> List[Dict]:
    api_key = SEARCH_REGISTRY.get(provider, "")
    try:
        if provider == "duckduckgo":
            from ddgs import DDGS
            results = DDGS().text(query, max_results=5)
            return [
                {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                for r in (results or [])
            ]
        if provider == "brave":
            import requests
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            return [
                {"title": r["title"], "url": r["url"], "snippet": r.get("description", "")}
                for r in resp.json().get("web", {}).get("results", [])
            ]
        if provider == "tavily":
            from tavily import TavilyClient
            resp = TavilyClient(api_key=api_key).search(query, max_results=5)
            return [
                {"title": r["title"], "url": r["url"], "snippet": r.get("content", "")}
                for r in resp.get("results", [])
            ]
        if provider == "serpapi":
            import requests
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": api_key, "num": 5},
                timeout=10,
            )
            resp.raise_for_status()
            return [
                {"title": r["title"], "url": r["link"], "snippet": r.get("snippet", "")}
                for r in resp.json().get("organic_results", [])
            ]
        if provider == "serper":
            import requests
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                data=json.dumps({"q": query, "num": 5}),
                timeout=10,
            )
            resp.raise_for_status()
            return [
                {"title": r["title"], "url": r["link"], "snippet": r.get("snippet", "")}
                for r in resp.json().get("organic", [])
            ]
    except Exception as e:
        logger.warning(f"search [{provider}] failed: {e}")
    return []


async def call_search(provider: str, query: str) -> List[Dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _search_sync, provider, query)


def _format_search_context(query: str, results: List[Dict]) -> str:
    lines = [
        "You have been provided with real-time web search results for the user's query.",
        "Use these results to answer. Do not say you cannot access the internet or search the web.",
        f"\n[Web search results for: '{query}']\n",
    ]
    for r in results:
        lines.append(f"• {r['title']}\n  {r['url']}\n  {r['snippet']}\n")
    return "\n".join(lines)

# ── Image adapters ─────────────────────────────────────────────────────────────

def _generate_image_sync(provider: str, prompt: str) -> bytes:
    api_key = IMAGE_REGISTRY.get(provider, "")
    try:
        if provider == "dalle":
            response = litellm.image_generation(
                model="dall-e-3", prompt=prompt, api_key=api_key, size="1024x1024"
            )
            import urllib.request
            with urllib.request.urlopen(response.data[0].url) as r:
                return r.read()

        if provider == "stability":
            import requests
            resp = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "image/png"},
                json={"text_prompts": [{"text": prompt}], "width": 1024, "height": 1024, "samples": 1},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.content

        if provider == "replicate":
            import requests, urllib.request
            resp = requests.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"input": {"prompt": prompt}},
                timeout=15,
            )
            resp.raise_for_status()
            pred_id = resp.json()["id"]
            for _ in range(30):
                time.sleep(2)
                r = requests.get(
                    f"https://api.replicate.com/v1/predictions/{pred_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                data = r.json()
                if data.get("status") == "succeeded":
                    with urllib.request.urlopen(data["output"][0]) as img_r:
                        return img_r.read()
                if data.get("status") == "failed":
                    break

        if provider == "fal":
            import requests, urllib.request
            resp = requests.post(
                "https://fal.run/fal-ai/flux/schnell",
                headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
                json={"prompt": prompt},
                timeout=60,
            )
            resp.raise_for_status()
            with urllib.request.urlopen(resp.json()["images"][0]["url"]) as r:
                return r.read()

    except Exception as e:
        logger.warning(f"image [{provider}] failed: {e}")
    return b""


async def call_image(provider: str, prompt: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _generate_image_sync, provider, prompt)

# ── Video adapters ─────────────────────────────────────────────────────────────

def _generate_video_sync(provider: str, prompt: str) -> bytes:
    api_key = VIDEO_REGISTRY.get(provider, "")
    try:
        if provider == "replicate":
            import requests, urllib.request
            resp = requests.post(
                "https://api.replicate.com/v1/models/minimax/video-01/predictions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"input": {"prompt": prompt, "duration": 5}},
                timeout=15,
            )
            resp.raise_for_status()
            pred_id = resp.json()["id"]
            for _ in range(90):
                time.sleep(2)
                r = requests.get(
                    f"https://api.replicate.com/v1/predictions/{pred_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                data = r.json()
                if data.get("status") == "succeeded":
                    url = data["output"]
                    if isinstance(url, list):
                        url = url[0]
                    with urllib.request.urlopen(url) as vr:
                        return vr.read()
                if data.get("status") == "failed":
                    logger.warning(f"video [replicate] failed: {data.get('error')}")
                    break

        if provider == "fal":
            import requests, urllib.request
            resp = requests.post(
                "https://queue.fal.run/fal-ai/kling-video/v1.6/standard/text-to-video",
                headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
                json={"prompt": prompt, "duration": "5"},
                timeout=15,
            )
            resp.raise_for_status()
            request_id = resp.json().get("request_id")
            if not request_id:
                return b""
            for _ in range(90):
                time.sleep(2)
                r = requests.get(
                    f"https://queue.fal.run/fal-ai/kling-video/v1.6/standard/text-to-video/requests/{request_id}/status",
                    headers={"Authorization": f"Key {api_key}"},
                )
                if r.json().get("status") == "COMPLETED":
                    result = requests.get(
                        f"https://queue.fal.run/fal-ai/kling-video/v1.6/standard/text-to-video/requests/{request_id}",
                        headers={"Authorization": f"Key {api_key}"},
                    ).json()
                    video_url = result.get("video", {}).get("url", "")
                    if video_url:
                        with urllib.request.urlopen(video_url) as vr:
                            return vr.read()
                    break
                if r.json().get("status") == "FAILED":
                    logger.warning("video [fal] generation failed")
                    break

    except Exception as e:
        logger.warning(f"video [{provider}] failed: {e}")
    return b""


async def call_video(provider: str, prompt: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _generate_video_sync, provider, prompt)

# ── Transcription adapters ─────────────────────────────────────────────────────

def _transcribe_sync(provider: str, audio_bytes: bytes) -> str:
    api_key = TRANSCRIPTION_REGISTRY.get(provider, "")
    try:
        if provider == "whisper":
            response = litellm.transcription(
                model="whisper-1",
                file=("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
                api_key=api_key,
            )
            return response.text

        if provider == "gemini":
            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode()
            response = litellm.completion(
                model="gemini/gemini-1.5-flash",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe this voice message accurately. Reply with only the transcription, nothing else."},
                        {"type": "image_url", "image_url": {"url": f"data:audio/ogg;base64,{audio_b64}"}},
                    ],
                }],
                api_key=api_key,
            )
            return response.choices[0].message.content

    except Exception as e:
        logger.warning(f"transcription [{provider}] failed: {e}")
    return ""


async def call_transcription(provider: str, audio_bytes: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _transcribe_sync, provider, audio_bytes)

# ── TTS adapters ───────────────────────────────────────────────────────────────

TTS_MAX_CHARS = 1500  # truncate before sending to TTS — long text causes timeouts


def _tts_sync(provider: str, text: str) -> bytes:
    api_key = TTS_REGISTRY.get(provider, "")
    if len(text) > TTS_MAX_CHARS:
        text = text[:TTS_MAX_CHARS] + "…"
    try:
        if provider == "elevenlabs":
            import requests
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_multilingual_v2"},
                timeout=90,
            )
            resp.raise_for_status()
            return resp.content

        if provider == "openai_tts":
            response = litellm.speech(
                model="tts-1", input=text, voice="alloy", api_key=api_key
            )
            return response.content if hasattr(response, "content") else b"".join(response)

    except Exception as e:
        logger.warning(f"tts [{provider}] failed: {e}")
    return b""


async def call_tts(provider: str, text: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _tts_sync, provider, text)

# ── LLM provider detection ─────────────────────────────────────────────────────

_ENV_TO_PROVIDER = {"google": "gemini"}

# Keys that belong to TTS / transcription / image / search — NOT LLM providers.
# Exclude them from the LLM registry scan so e.g. ELEVENLABS_API_KEY never
# appears as an LLM provider.
_NON_LLM_API_KEYS = frozenset(
    list(_TTS_KEY_MAP) + list(_TRANSCRIPTION_KEY_MAP) +
    list(_IMAGE_KEY_MAP) + list(_VIDEO_KEY_MAP) + list(_SEARCH_KEY_MAP)
)

# ── Key rotation (multiple API keys per provider) ──────────────────────────────

def _build_provider_keys() -> Dict[str, List[str]]:
    """Parse all LLM API keys per provider.
    Supports PROVIDER_API_KEY (primary) and PROVIDER_API_KEY_2, _3, ... (extras)."""
    buckets: Dict[str, Dict[int, str]] = {}
    for k, v in os.environ.items():
        if not v:
            continue
        m = _re.match(r'^(.+?)_API_KEY(?:_(\d+))?$', k)
        if not m:
            continue
        base = f"{m.group(1)}_API_KEY"
        if base in _NON_LLM_API_KEYS:
            continue
        raw      = m.group(1).lower()
        provider = _ENV_TO_PROVIDER.get(raw, raw)
        idx      = int(m.group(2)) if m.group(2) else 0
        buckets.setdefault(provider, {})[idx] = v
    return {p: [v for _, v in sorted(d.items())] for p, d in buckets.items()}


PROVIDER_KEYS: Dict[str, List[str]] = {}  # populated after MODEL_REGISTRY
KEY_INDEX:     Dict[str, int]       = {}  # provider → index of currently active key
KEY_SWITCHABLE_PROVIDERS: set[str]  = set()

# ───────────────────────────────────────────────────────────────────────────────

if os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]


def parse_env_providers() -> Dict[str, str]:
    providers = {}
    for key, value in os.environ.items():
        if not key.endswith("_API_KEY") or not value:
            continue
        if key in _NON_LLM_API_KEYS:
            continue
        raw      = key.removesuffix("_API_KEY").lower()
        provider = _ENV_TO_PROVIDER.get(raw, raw)
        providers[provider] = value
    return providers


def get_kilocode_models(api_key: str) -> List[str]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.kilo.ai/api/gateway/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        models = []
        for m in (data.get("data", data) if isinstance(data, dict) else data):
            model_id = m.get("id", "") if isinstance(m, dict) else str(m)
            if model_id:
                models.append(model_id)
        skip = ("embed", "tts", "image", "whisper", "moderat", "audio")
        return sorted(m for m in models if not any(s in m.lower() for s in skip))
    except Exception as e:
        logger.warning(f"Kilocode model fetch failed: {e}")
        return ["z-ai/glm-5", "minimax/minimax-m2.5"]


def get_models_for_provider(provider: str) -> List[str]:
    all_models  = litellm.models_by_provider.get(provider, [])
    prefix      = f"{provider}/"
    bare        = [m[len(prefix):] if m.startswith(prefix) else m for m in all_models]
    known       = set(litellm.model_cost.keys())
    chat_models = [m for m in bare if f"{provider}/{m}" in known or m in known]
    skip = ("embed", "tts", "dall-e", "whisper", "moderat", "audio",
            "realtime", "image", "search", "computer", "live")
    return sorted(m for m in chat_models if not any(s in m.lower() for s in skip))


def get_ollama_models() -> List[str]:
    import subprocess
    for cmd in [["podman","exec","ollama","ollama","list"],
                ["docker","exec","ollama","ollama","list"],
                ["ollama","list"]]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                continue
            models = [line.split()[0] for line in result.stdout.strip().splitlines()[1:] if line.split()]
            if models:
                return sorted(models)
        except Exception:
            pass
    return []


def get_openai_url_models() -> Dict[str, dict]:
    """Discover models from OPENAI_URL, OPENAI_URL_2, ... in host.conf.
    Returns {provider_name: {url, key, models}} for each reachable endpoint."""
    import urllib.request as _ureq
    import json as _json
    from urllib.parse import urlparse
    result = {}
    idx = 1
    while idx <= 10:
        suffix = "" if idx == 1 else f"_{idx}"
        url = os.getenv(f"OPENAI_URL{suffix}", "").rstrip("/")
        if not url:
            if idx > 1:
                break
            idx += 1
            continue
        key = os.getenv(f"OPENAI_URL{suffix}_KEY", "lm-studio")
        parsed = urlparse(url)
        provider = parsed.hostname or f"host{idx}"
        try:
            req = _ureq.Request(
                f"{url}/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            with _ureq.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read())
            models = [m["id"] for m in data.get("data", []) if m.get("id")]
            if models:
                result[provider] = {"url": url, "key": key, "models": models}
                logger.info(f"host.conf {provider}: {len(models)} model(s): {models}")
            else:
                logger.warning(f"host.conf {provider} ({url}): reachable but no models returned")
        except Exception as e:
            logger.warning(f"host.conf OPENAI_URL{suffix} ({url}): {e}")
        idx += 1
    return result


# populated by build_model_registry(); used in completion routing
OPENAI_URL_MAP: Dict[str, dict] = {}


def build_model_registry() -> Dict[str, List[str]]:
    registry = {}
    for provider, api_key in parse_env_providers().items():
        if provider == "kilocode":
            models = get_kilocode_models(api_key)
            if models:
                registry["kilocode"] = models
            continue
        models = get_models_for_provider(provider)
        if models:
            registry[provider] = models
    ollama = get_ollama_models()
    if ollama:
        registry["ollama"] = ollama
    url_providers = get_openai_url_models()
    OPENAI_URL_MAP.update(url_providers)
    for pname, info in url_providers.items():
        registry[pname] = info["models"]
    return registry


MODEL_REGISTRY = build_model_registry()
logger.info(f"LLM providers: {list(MODEL_REGISTRY.keys())}")

PROVIDER_KEYS = _build_provider_keys()
_multi = {p: len(ks) for p, ks in PROVIDER_KEYS.items() if len(ks) > 1}
KEY_SWITCHABLE_PROVIDERS = set(_multi.keys())
if _multi:
    logger.info(f"Key rotation enabled: {_multi}")

DEFAULT_SETTINGS = {"thinking": "medium", "temperature": 0.7, "max_tokens": 4000}

# ── State ──────────────────────────────────────────────────────────────────────

class BotState:
    def __init__(self):
        self.current_model          = self._pick_default()
        self.conversation:          List[Dict] = []
        self.settings               = DEFAULT_SETTINGS.copy()
        self.favorites:             List[str] = []
        self.search_enabled         = False
        self.search_provider        = "duckduckgo"
        self.search_rag_mode        = False
        self.image_provider         = next(iter(IMAGE_REGISTRY), "")
        self.video_provider         = next(iter(VIDEO_REGISTRY), "")
        self.transcription_provider = next(iter(TRANSCRIPTION_REGISTRY), "")
        self.tts_enabled            = False
        self.tts_provider           = next(iter(TTS_REGISTRY), "")
        self.parallel_tool_calls    = True
        self.fallback_model         = ""
        self.load_favorites()
        self.load_current()

    def _pick_default(self) -> str:
        for prov, model in [("anthropic","claude-sonnet-4-6"),("openai","gpt-4o"),("gemini","gemini-2.5-flash")]:
            if prov in MODEL_REGISTRY and model in MODEL_REGISTRY[prov]:
                return f"{prov}/{model}"
        for prov, models in MODEL_REGISTRY.items():
            if models:
                return f"{prov}/{models[0]}"
        return "openai/gpt-4o"

    def load_favorites(self):
        if FAVORITES_FILE.exists():
            try:
                self.favorites = json.loads(FAVORITES_FILE.read_text())
            except Exception:
                self.favorites = []

    def save_favorites(self):
        FAVORITES_FILE.write_text(json.dumps(self.favorites, indent=2))

    def toggle_favorite(self, model_key: str) -> bool:
        if model_key in self.favorites:
            self.favorites.remove(model_key)
            self.save_favorites()
            return False
        self.favorites.append(model_key)
        self.save_favorites()
        return True

    def load_current(self):
        if CURRENT_CONV_FILE.exists():
            try:
                with open(CURRENT_CONV_FILE) as f:
                    data = json.load(f)
                saved = data.get("model", self.current_model)
                prov  = saved.split("/")[0] if "/" in saved else ""
                name  = saved.split("/", 1)[1] if "/" in saved else saved
                if prov in MODEL_REGISTRY and name in MODEL_REGISTRY[prov]:
                    self.current_model = saved
                self.conversation          = data.get("messages", [])
                self.settings              = data.get("settings", DEFAULT_SETTINGS.copy())
                self.search_enabled        = data.get("search_enabled", False)
                self.search_provider       = data.get("search_provider", "duckduckgo")
                self.search_rag_mode       = data.get("search_rag_mode", False)
                self.image_provider        = data.get("image_provider", next(iter(IMAGE_REGISTRY), ""))
                self.video_provider        = data.get("video_provider", next(iter(VIDEO_REGISTRY), ""))
                self.transcription_provider= data.get("transcription_provider", next(iter(TRANSCRIPTION_REGISTRY), ""))
                self.tts_enabled           = data.get("tts_enabled", False)
                self.tts_provider          = data.get("tts_provider", next(iter(TTS_REGISTRY), ""))
                self.parallel_tool_calls   = data.get("parallel_tool_calls", True)
                self.fallback_model        = data.get("fallback_model", "")
            except Exception as e:
                logger.error(f"load_current: {e}")

    def save_current(self):
        data = {
            "model":                   self.current_model,
            "messages":                self.conversation,
            "settings":                self.settings,
            "search_enabled":          self.search_enabled,
            "search_provider":         self.search_provider,
            "search_rag_mode":         self.search_rag_mode,
            "image_provider":          self.image_provider,
            "video_provider":          self.video_provider,
            "transcription_provider":  self.transcription_provider,
            "tts_enabled":             self.tts_enabled,
            "tts_provider":            self.tts_provider,
            "parallel_tool_calls":     self.parallel_tool_calls,
            "fallback_model":          self.fallback_model,
            "timestamp":               datetime.now().isoformat(),
        }
        with open(CURRENT_CONV_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def add_message(self, role: str, content):
        self.conversation.append({"role": role, "content": content})
        self.save_current()

    def clear_conversation(self):
        self.conversation = []
        self.save_current()


state = BotState()

# ── Key-rotating litellm wrapper ───────────────────────────────────────────────

def _completion_with_rotation(provider: str, fallback_model: str,
                              side_effects: Optional[list], **kwargs):
    """litellm.completion with automatic key rotation on RateLimitError.

    On rate limit:
      1. Rotate to next key for the same provider (notifies via side_effects).
      2. If all keys exhausted and fallback_model is set, switch to it (notifies).
      3. Otherwise re-raise.
    """
    keys        = _build_provider_keys().get(provider, [])
    tried_fback = False

    def _maybe_rotate_current_key(reason: str) -> bool:
        """Advance to next key for same provider if available."""
        nxt = KEY_INDEX.get(provider, 0) + 1
        if nxt < len(keys):
            KEY_INDEX[provider] = nxt
            kwargs["api_key"]   = keys[nxt]
            msg = f"⚠️ {reason} — rotated to *{provider}* key {nxt + 1}/{len(keys)}"
            logger.warning(msg.replace("*", ""))
            if side_effects is not None:
                side_effects.append({"type": "notify", "text": msg})
            return True
        return False

    def _is_auth_or_dead_key_error(exc: Exception) -> bool:
        """Best-effort detection for dead / blocked / invalid provider keys."""
        msg = str(exc).lower()
        markers = (
            "invalid_api_key",
            "invalid api key",
            "incorrect api key",
            "authenticationerror",
            "authentication error",
            "autherror",
            "unauthorized",
            "forbidden",
            "permission denied",
            "permission_error",
            "invalid x-api-key",
            "api key expired",
            "key has been disabled",
            "key revoked",
            "credit balance is too low",
            "insufficient credits",
            "account suspended",
            "billing",
            "invalid_request_error",
            "client specified an invalid argument",
            "api key failed",
            "model not found",
        )
        return any(marker in msg for marker in markers)

    while True:
        try:
            return litellm.completion(**kwargs)

        except litellm.RateLimitError:
            if _maybe_rotate_current_key("Rate limit"):
                continue

            if fallback_model and not tried_fback:
                tried_fback = True
                msg = f"⚠️ All *{provider}* keys rate-limited → switching to fallback: `{fallback_model}`"
                logger.warning(msg.replace("*", "").replace("`", ""))
                if side_effects is not None:
                    side_effects.append({"type": "notify", "text": msg})

                fp = fallback_model.split("/")[0] if "/" in fallback_model else ""
                kwargs.pop("api_key",  None)
                kwargs.pop("api_base", None)
                if fallback_model.startswith("ollama/"):
                    kwargs["model"]    = fallback_model
                    kwargs["api_base"] = "http://localhost:11434"
                elif fallback_model.startswith("kilocode/"):
                    kwargs["model"]    = f"openai/{fallback_model.split('/', 1)[1]}"
                    kwargs["api_base"] = "https://api.kilo.ai/api/gateway/"
                    kwargs["api_key"]  = os.getenv("KILOCODE_API_KEY", "")
                elif (fp := fallback_model.split("/")[0]) in OPENAI_URL_MAP:
                    info = OPENAI_URL_MAP[fp]
                    kwargs["model"]    = f"openai/{fallback_model.split('/', 1)[1]}"
                    kwargs["api_base"] = info["url"]
                    kwargs["api_key"]  = info["key"]
                else:
                    kwargs["model"] = fallback_model

                provider = fp
                keys     = _build_provider_keys().get(provider, [])
                KEY_INDEX.pop(provider, None)
                continue

            raise

        except Exception as e:
            if _is_auth_or_dead_key_error(e) and _maybe_rotate_current_key("API key failed"):
                continue
            raise


# ── LLM call (with tool calling + RAG fallback) ────────────────────────────────

def _call_llm_sync(model_key: str, messages: List[Dict], settings: Dict,
                   search_provider: Optional[str] = None,
                   image_provider:  Optional[str] = None,
                   side_effects:    Optional[list] = None) -> str:

    chat_history = [
        m for m in messages
        if not (m.get("role") == "user" and isinstance(m.get("content"), str) and m["content"].startswith("/"))
    ]
    kwargs: Dict = {"messages": chat_history, "timeout": LLM_TIMEOUT}
    provider = model_key.split("/")[0] if "/" in model_key else model_key
    _fallback = state.fallback_model
    if settings.get("temperature") is not None:
        kwargs["temperature"] = settings["temperature"]
    if settings.get("max_tokens") is not None:
        kwargs["max_tokens"] = settings["max_tokens"]

    def _first_text(c):
        if isinstance(c, list):
            return next((p.get("text", "") for p in c if p.get("type") == "text"), "")
        return c or ""
    user_msg = next((_first_text(m["content"]) for m in reversed(chat_history) if m.get("role") == "user"), "")
    logger.info(f">>> [{model_key}] {user_msg[:120]}")

    if model_key.startswith("kilocode/"):
        kwargs["model"]    = f"openai/{model_key.split('/',1)[1]}"
        kwargs["api_base"] = "https://api.kilo.ai/api/gateway/"
        kwargs["api_key"]  = os.getenv("KILOCODE_API_KEY")
    elif model_key.startswith("ollama/"):
        kwargs["model"]    = model_key
        kwargs["api_base"] = "http://localhost:11434"
    elif (prov := model_key.split("/")[0]) in OPENAI_URL_MAP:
        info = OPENAI_URL_MAP[prov]
        kwargs["model"]    = f"openai/{model_key.split('/', 1)[1]}"
        kwargs["api_base"] = info["url"]
        kwargs["api_key"]  = info["key"]
    else:
        kwargs["model"] = model_key

    # Inject current date/time into chat_history itself so it survives every
    # kwargs["messages"] = chat_history reassignment inside the tool loop
    _now = datetime.now()
    _sys = (
        f"You are an AI assistant powered by {model_key}. "
        f"Today is {_now.strftime('%A, %d %B %Y')}. Current time: {_now.strftime('%H:%M')} (local)."
    )
    if not any(m.get("role") == "system" for m in chat_history):
        chat_history = [{"role": "system", "content": _sys}] + chat_history
    else:
        chat_history = [
            {**m, "content": f"{_sys}\n\n{m['content']}"} if m.get("role") == "system" else m
            for m in chat_history
        ]
    kwargs["messages"] = chat_history

    # RAG mode: inject search results directly, skip tool calling entirely
    if search_provider and state.search_rag_mode:
        user_query = next(
            (m["content"] for m in reversed(chat_history) if m.get("role") == "user"), ""
        )
        logger.info(f"    [RAG] searching: {user_query[:80]}")
        results = _search_sync(search_provider, user_query)
        if results:
            ctx = _format_search_context(user_query, results)
            kwargs["messages"] = [{"role": "system", "content": ctx}] + chat_history
        response = _completion_with_rotation(provider, _fallback, side_effects, **kwargs)
        reply = response.choices[0].message.content or ""
        logger.info(f"<<< [{model_key}] {reply[:120]}")
        return reply

    # Build tools list dynamically
    tools = []
    if search_provider:
        tools.append(SEARCH_TOOL)
    if image_provider and IMAGE_REGISTRY:
        tools.append(IMAGE_TOOL)
    tools.append(DOCUMENT_TOOL)

    if tools:
        try:
            kwargs["tools"]       = tools
            kwargs["tool_choice"] = "auto"
            if state.parallel_tool_calls:
                kwargs["parallel_tool_calls"] = True
            response = _completion_with_rotation(provider, _fallback, side_effects, **kwargs)

            for _ in range(8):
                if response.choices[0].finish_reason != "tool_calls":
                    break
                tool_calls = response.choices[0].message.tool_calls
                chat_history.append(response.choices[0].message)

                for tc in tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)

                    if name == "web_search" and search_provider:
                        query_ = args.get("query", "")
                        logger.info(f"    [tool] web_search: {query_[:80]}")
                        results = _search_sync(search_provider, query_)
                        content = _format_search_context(args["query"], results) if results else "No results found."

                    elif name == "generate_image" and image_provider:
                        prompt    = args.get("prompt", "")
                        logger.info(f"    [tool] generate_image: {prompt[:80]}")
                        img_bytes = _generate_image_sync(image_provider, prompt)
                        if side_effects is not None:
                            side_effects.append({"type": "image", "data": img_bytes})
                        content = f"Image generated: '{prompt}'" if img_bytes else f"Image generation failed for: '{prompt}'"

                    elif name == "generate_document":
                        filename = args.get("filename", "document.txt")
                        doc_content = args.get("content", "")
                        logger.info(f"    [tool] generate_document: {filename}")
                        if side_effects is not None:
                            side_effects.append({"type": "document", "filename": filename, "data": doc_content.encode()})
                        content = f"Document '{filename}' generated and will be sent as a file attachment. Do not repeat the file content in your text reply."

                    else:
                        content = f"Unknown tool: {name}"

                    chat_history.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "name": name,   "content": content,
                    })

                kwargs["messages"] = chat_history
                response = _completion_with_rotation(provider, _fallback, side_effects, **kwargs)

            reply = response.choices[0].message.content
            logger.info(f"<<< [{model_key}] {(reply or '')[:120]}")
            return reply

        except Exception as e:
            logger.warning(f"Tool calling failed ({e}) — falling back to RAG")
            kwargs.pop("tools", None)
            kwargs.pop("tool_choice", None)
            if search_provider:
                user_query = next(
                    (m["content"] for m in reversed(chat_history) if m.get("role") == "user"), ""
                )
                results = _search_sync(search_provider, user_query)
                if results:
                    ctx = _format_search_context(user_query, results)
                    kwargs["messages"] = [{"role": "system", "content": ctx}] + chat_history

    response = _completion_with_rotation(provider, _fallback, side_effects, **kwargs)
    reply = response.choices[0].message.content or ""
    logger.info(f"<<< [{model_key}] {reply[:120]}")
    return reply


async def call_llm(model_key: str, messages: List[Dict], settings: Dict,
                   search_provider: Optional[str] = None,
                   image_provider:  Optional[str] = None,
                   side_effects:    Optional[list] = None) -> str:
    loop = asyncio.get_event_loop()
    fn   = functools.partial(
        _call_llm_sync, model_key, messages, settings,
        search_provider, image_provider, side_effects
    )
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_executor, fn),
            timeout=LLM_TIMEOUT + 10,
        )
    except asyncio.TimeoutError:
        return f"⏱ Timeout: {model_key} did not respond in {LLM_TIMEOUT}s."
    except Exception as e:
        logger.error(f"call_llm {model_key}: {e}")
        return f"❌ Error: {e}"

# ── Helper: process side effects (notifications, images, documents) ────────────

async def _handle_side_effects(update: Update, side_effects: list):
    for effect in side_effects:
        if effect["type"] == "notify":
            await update.message.reply_text(effect["text"], parse_mode="Markdown")
        elif effect["type"] == "image" and effect.get("data"):
            await update.message.reply_photo(io.BytesIO(effect["data"]))
        elif effect["type"] == "document" and effect.get("data"):
            await update.message.reply_document(
                io.BytesIO(effect["data"]), filename=effect["filename"]
            )

# ── Helper: send LLM response (text or TTS voice) ─────────────────────────────

async def _send_response(update: Update, response: str):
    """Send text response, or voice if TTS is enabled."""
    if not response or not response.strip():
        await update.message.reply_text("⚠️ Model returned an empty response.")
        return
    if state.tts_enabled and TTS_REGISTRY and state.tts_provider:
        tts_bytes = await call_tts(state.tts_provider, response)
        if tts_bytes:
            await update.message.reply_voice(io.BytesIO(tts_bytes))
            return
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i:i + 4000])
    else:
        await update.message.reply_text(response)

# ── UI helpers (models) ────────────────────────────────────────────────────────

async def _show_providers(query):
    keyboard = []
    if state.favorites:
        keyboard.append([InlineKeyboardButton(
            f"⭐ Favorites ({len(state.favorites)})", callback_data="prov:__fav__:0"
        )])
    for prov in sorted(MODEL_REGISTRY.keys()):
        icon = "🟢" if state.current_model.startswith(prov + "/") else "⚪"
        keyboard.append([InlineKeyboardButton(
            f"{icon} {prov} ({len(MODEL_REGISTRY[prov])})", callback_data=f"prov:{prov}:0"
        )])
    await query.edit_message_text(
        f"Select provider:\n(current: `{state.current_model}`)",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
    )


async def _show_model_page(query, provider: str, page: int, fav_edit: bool = False):
    models = MODEL_REGISTRY.get(provider, [])
    if not models:
        await query.edit_message_text(f"❌ No models for {provider}")
        return
    total = len(models)
    start = page * MODELS_PER_PAGE
    end   = min(start + MODELS_PER_PAGE, total)
    keyboard = []
    for m in models[start:end]:
        full_key = f"{provider}/{m}"
        is_fav   = full_key in state.favorites
        current  = "✓ " if full_key == state.current_model else ""
        if fav_edit:
            label, cb = f"{'⭐' if is_fav else '☆'} {m}", f"fav:{provider}:{page}:{m}"
        else:
            label, cb = f"{current}{'⭐ ' if is_fav else ''}{m}", f"model:{full_key}"
        if len(cb.encode()) <= 64:
            keyboard.append([InlineKeyboardButton(label, callback_data=cb)])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"{'faved' if fav_edit else 'prov'}:{provider}:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"{'faved' if fav_edit else 'prov'}:{provider}:{page+1}"))
    if nav:
        keyboard.append(nav)
    if fav_edit:
        keyboard.append([InlineKeyboardButton("✓ Done",           callback_data=f"prov:{provider}:{page}")])
    else:
        keyboard.append([InlineKeyboardButton("☆ Edit Favorites", callback_data=f"faved:{provider}:{page}")])
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="prov:__back__:0")])
    pages_total = (total + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE
    await query.edit_message_text(
        f"*{provider}* — {total} models (page {page+1}/{pages_total}):\n"
        f"{'Tap to toggle ⭐' if fav_edit else 'Tap to select'}",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
    )


async def _show_favorites_page(query, page: int, removing: bool = False):
    favs = sorted(state.favorites)
    if not favs:
        await query.edit_message_text("❌ No favorites yet. Use /models → browse a provider → ☆ Edit Favorites")
        return
    total = len(favs)
    start = page * MODELS_PER_PAGE
    end   = min(start + MODELS_PER_PAGE, total)
    keyboard = []
    for full_key in favs[start:end]:
        if removing:
            label, cb = f"❌ {full_key}", f"fav:rm:{full_key}"
        else:
            label, cb = f"{'✓ ' if full_key == state.current_model else ''}{full_key}", f"model:{full_key}"
        if len(cb.encode()) <= 64:
            keyboard.append([InlineKeyboardButton(label, callback_data=cb)])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"{'favrm' if removing else 'prov'}:__fav__:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"{'favrm' if removing else 'prov'}:__fav__:{page+1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("✓ Done" if removing else "🗑 Remove",
                                          callback_data=f"prov:__fav__:{page}" if removing else f"favrm:__fav__:{page}")])
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="prov:__back__:0")])
    pages_total = (total + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE
    await query.edit_message_text(
        f"⭐ *Favorites* — {total} models (page {page+1}/{pages_total}):\n"
        f"{'Tap to remove' if removing else 'Tap to select'}",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
    )

# ── Command handlers ───────────────────────────────────────────────────────────

async def models_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MODEL_REGISTRY
    MODEL_REGISTRY = build_model_registry()
    if not MODEL_REGISTRY:
        await update.message.reply_text("❌ No API keys found in .env")
        return
    keyboard = []
    if state.favorites:
        keyboard.append([InlineKeyboardButton(f"⭐ Favorites ({len(state.favorites)})", callback_data="prov:__fav__:0")])
    for prov in sorted(MODEL_REGISTRY.keys()):
        icon = "🟢" if state.current_model.startswith(prov + "/") else "⚪"
        keyboard.append([InlineKeyboardButton(f"{icon} {prov} ({len(MODEL_REGISTRY[prov])})", callback_data=f"prov:{prov}:0")])
    await update.message.reply_text(
        f"Select provider:\n(current: `{state.current_model}`)",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
    )


async def fav_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.favorites:
        await update.message.reply_text("⭐ No favorites yet.\nUse /models → browse a provider → ☆ Edit Favorites")
        return
    keyboard = []
    for full_key in sorted(state.favorites):
        cb = f"model:{full_key}"
        if len(cb.encode()) <= 64:
            keyboard.append([InlineKeyboardButton(
                f"{'✓ ' if full_key == state.current_model else ''}{full_key}", callback_data=cb
            )])
    keyboard.append([InlineKeyboardButton("🗑 Remove", callback_data="favrm:__fav__:0")])
    await update.message.reply_text(
        f"⭐ *Favorites* — {len(state.favorites)} models:\nTap to select",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
    )


async def newconversation_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = len(state.conversation)
    state.clear_conversation()
    await update.message.reply_text(f"✅ New conversation started\n(Cleared {count} messages)")


async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.conversation:
        await update.message.reply_text("❌ No conversation to save")
        return
    if context.args:
        name = " ".join(context.args)
    else:
        await update.message.reply_text("💾 Reply with a name for this conversation:")
        context.user_data["awaiting_save_name"] = True
        return
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename  = f"{name.lower().replace(' ', '-')}_{timestamp}.json"
    data = {"name": name, "timestamp": timestamp, "model": state.current_model,
            "messages": state.conversation, "settings": state.settings}
    with open(CONVERSATIONS_DIR / filename, "w") as f:
        json.dump(data, f, indent=2)
    await update.message.reply_text(f"✅ Saved: {filename}\n({len(state.conversation)} messages)")


async def load_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = sorted(CONVERSATIONS_DIR.glob("*.json"), reverse=True)
    if not files:
        await update.message.reply_text("❌ No saved conversations")
        return
    keyboard = []
    for f in files[:10]:
        try:
            with open(f) as fh:
                data = json.load(fh)
            keyboard.append([InlineKeyboardButton(
                f"{data.get('name', f.stem)} ({len(data.get('messages',[]))} msgs) — {data.get('timestamp','')[:10]}",
                callback_data=f"load:{f.name}",
            )])
        except Exception:
            continue
    if not keyboard:
        await update.message.reply_text("❌ No valid conversations found")
        return
    await update.message.reply_text("Select conversation to load:", reply_markup=InlineKeyboardMarkup(keyboard))


def _fmt(val) -> str:
    return "Default" if val is None else str(val)


def _mask_key(key: str) -> str:
    """Short human-readable key mask like sk-123...11234."""
    if not key:
        return "empty"
    if len(key) <= 10:
        return key[:3] + "..." + key[-2:]
    return key[:6] + "..." + key[-5:]


def _current_provider_keys(provider: str) -> List[str]:
    """Re-read provider keys dynamically from current env."""
    global PROVIDER_KEYS
    PROVIDER_KEYS = _build_provider_keys()
    return PROVIDER_KEYS.get(provider, [])


def _build_settings_view() -> tuple[str, InlineKeyboardMarkup]:
    prov = state.current_model.split("/")[0] if "/" in state.current_model else state.current_model
    keys = _current_provider_keys(prov)
    switchable = prov in KEY_SWITCHABLE_PROVIDERS and len(keys) > 1
    keyboard = [
        [InlineKeyboardButton("🧠 Thinking: Default", callback_data="set:thinking:default"),
         InlineKeyboardButton("Low",    callback_data="set:thinking:low"),
         InlineKeyboardButton("Medium", callback_data="set:thinking:medium"),
         InlineKeyboardButton("High",   callback_data="set:thinking:high")],
        [InlineKeyboardButton("🌡️ Temp: Default",    callback_data="set:temp:default"),
         InlineKeyboardButton("0.3",  callback_data="set:temp:0.3"),
         InlineKeyboardButton("0.7",  callback_data="set:temp:0.7"),
         InlineKeyboardButton("1.0",  callback_data="set:temp:1.0")],
        [InlineKeyboardButton("📏 Tokens: Default",  callback_data="set:tokens:default"),
         InlineKeyboardButton("2000", callback_data="set:tokens:2000"),
         InlineKeyboardButton("4000", callback_data="set:tokens:4000"),
         InlineKeyboardButton("8000", callback_data="set:tokens:8000")],
        [InlineKeyboardButton(
            f"⚡ Parallel tool calls: {'ON ✅' if state.parallel_tool_calls else 'OFF ❌'}",
            callback_data="set:parallel:toggle")],
        [InlineKeyboardButton(
            f"🔀 Fallback: {state.fallback_model or '—  (tap to set)'}",
            callback_data="set:fallback:pick"),
         InlineKeyboardButton("✕ Clear", callback_data="set:fallback:clear")],
    ]
    if switchable:
        active_idx = KEY_INDEX.get(prov, 0)
        if active_idx >= len(keys):
            active_idx = 0
            KEY_INDEX[prov] = 0
        for idx, key in enumerate(keys):
            prefix = "✓ " if idx == active_idx else ""
            keyboard.append([InlineKeyboardButton(
                f"{prefix}🔑 {prov} {idx + 1}/{len(keys)} {_mask_key(key)}",
                callback_data=f"set:keyidx:{idx}",
            )])
    parallel_status = "ON ✅" if state.parallel_tool_calls else "OFF ❌"
    key_info = ""
    if switchable:
        active_idx = KEY_INDEX.get(prov, 0)
        active_key = keys[active_idx] if active_idx < len(keys) else keys[0]
        key_info = f"\n🔑 Active key: {active_idx + 1}/{len(keys)} `{_mask_key(active_key)}`"
    text = (
        f"*Current Settings:*\n"
        f"Thinking: {_fmt(state.settings['thinking'])}\n"
        f"Temperature: {_fmt(state.settings['temperature'])}\n"
        f"Max Tokens: {_fmt(state.settings['max_tokens'])}\n"
        f"Parallel tool calls: {parallel_status}\n"
        f"Fallback model: {state.fallback_model or '—'}"
    )
    return text + key_info, InlineKeyboardMarkup(keyboard)


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, markup = _build_settings_view()
    await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search = f"🔍 {state.search_provider}" if state.search_enabled else "off"
    image  = f"🎨 {state.image_provider}" if IMAGE_REGISTRY else "no keys"
    tts    = f"🔊 {state.tts_provider}" if state.tts_enabled else "off"
    trans  = state.transcription_provider if TRANSCRIPTION_REGISTRY else "no keys"
    prov   = state.current_model.split("/")[0] if "/" in state.current_model else state.current_model
    keys   = _current_provider_keys(prov)
    switchable = prov in KEY_SWITCHABLE_PROVIDERS and len(keys) > 1
    key_info = ""
    if switchable:
        active_idx = KEY_INDEX.get(prov, 0)
        if active_idx >= len(keys):
            active_idx = 0
            KEY_INDEX[prov] = 0
        active_key = keys[active_idx]
        key_info = f" (key {active_idx + 1}/{len(keys)} {_mask_key(active_key)})"
    fallback_info = f"\n🔀 Fallback: `{state.fallback_model}`" if state.fallback_model else ""
    await update.message.reply_text(
        f"*Current Status:*\n\n"
        f"🤖 Model: `{state.current_model}`{key_info}\n"
        f"💬 Messages: {len(state.conversation)}\n"
        f"🔍 Web search: {search}\n"
        f"🎨 Image: {image}\n"
        f"🎤 Transcription: {trans}\n"
        f"🔊 TTS: {tts}\n"
        f"🧠 Thinking: {_fmt(state.settings['thinking'])}\n"
        f"🌡️ Temperature: {_fmt(state.settings['temperature'])}\n"
        f"📏 Max Tokens: {_fmt(state.settings['max_tokens'])}"
        f"{fallback_info}",
        parse_mode="Markdown",
    )


async def websearch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SEARCH_REGISTRY
    SEARCH_REGISTRY = build_search_registry()
    if list(SEARCH_REGISTRY.keys()) == ["duckduckgo"]:
        state.search_enabled  = not state.search_enabled
        state.search_provider = "duckduckgo"
        state.save_current()
        status = "🔍 ON (duckduckgo)" if state.search_enabled else "🔍 OFF"
        await update.message.reply_text(f"Web search: {status}")
        return
    keyboard = []
    for prov in SEARCH_REGISTRY:
        active = "✓ " if (state.search_enabled and state.search_provider == prov) else ""
        icon   = "🦆" if prov == "duckduckgo" else "🔍"
        keyboard.append([InlineKeyboardButton(f"{active}{icon} {prov}", callback_data=f"ws:{prov}")])
    rag_label = "✓ RAG inject" if state.search_rag_mode else "☐ RAG inject"
    keyboard.append([InlineKeyboardButton(f"{rag_label} (for small models)", callback_data="ws:__rag__")])
    if state.search_enabled:
        keyboard.append([InlineKeyboardButton("❌ Disable search", callback_data="ws:__off__")])
    mode   = "RAG" if state.search_rag_mode else "tool calling"
    status = f"active: {state.search_provider} [{mode}]" if state.search_enabled else "disabled"
    await update.message.reply_text(
        f"🔍 Web search — {status}\nSelect provider:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Raw search — returns results directly without going through the LLM."""
    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return
    query    = " ".join(context.args)
    provider = state.search_provider if state.search_enabled else "duckduckgo"
    await update.message.chat.send_action("typing")
    results  = await call_search(provider, query)
    if not results:
        await update.message.reply_text(f"🔍 No results for: {query}")
        return
    lines = [f"🔍 *{provider}* — {query}\n"]
    for r in results:
        lines.append(f"• [{r['title']}]({r['url']})\n  {r['snippet'][:120]}...\n")
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True
    )


async def imagine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global IMAGE_REGISTRY
    IMAGE_REGISTRY = build_image_registry()
    if not IMAGE_REGISTRY:
        await update.message.reply_text(
            "❌ No image keys configured.\n"
            "Copy `imageenv.example` → `.imageenv` and add at least one key."
        )
        return
    if not context.args:
        # Show provider selection
        keyboard = []
        for prov in IMAGE_REGISTRY:
            active = "✓ " if prov == state.image_provider else ""
            keyboard.append([InlineKeyboardButton(f"{active}🎨 {prov}", callback_data=f"imgset:{prov}")])
        await update.message.reply_text(
            f"🎨 Image provider: *{state.image_provider or '—'}*\n"
            "Select provider or use `/imagine <description>`:",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
        )
        return
    prompt = " ".join(context.args)
    await update.message.chat.send_action("upload_photo")
    img_bytes = await call_image(state.image_provider, prompt)
    if not img_bytes:
        await update.message.reply_text("❌ Image generation failed")
        return
    await update.message.reply_photo(io.BytesIO(img_bytes), caption=f"🎨 {prompt[:200]}")


async def video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global VIDEO_REGISTRY
    VIDEO_REGISTRY = build_video_registry()
    if not VIDEO_REGISTRY:
        await update.message.reply_text(
            "❌ No video keys configured.\n"
            "Add REPLICATE_API_KEY or FAL_API_KEY to .imageenv."
        )
        return
    if not context.args:
        keyboard = []
        for prov in VIDEO_REGISTRY:
            active = "✓ " if prov == state.video_provider else ""
            keyboard.append([InlineKeyboardButton(f"{active}🎬 {prov}", callback_data=f"vidset:{prov}")])
        await update.message.reply_text(
            f"🎬 Video provider: *{state.video_provider or '—'}*\n"
            "Select provider or use `/video <description>`:",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
        )
        return
    prompt = " ".join(context.args)
    await update.message.chat.send_action("upload_video")
    vid_bytes = await call_video(state.video_provider, prompt)
    if not vid_bytes:
        await update.message.reply_text("❌ Video generation failed")
        return
    await update.message.reply_video(io.BytesIO(vid_bytes), caption=f"🎬 {prompt[:200]}")


async def tts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TTS_REGISTRY
    TTS_REGISTRY = build_tts_registry()
    if not TTS_REGISTRY:
        await update.message.reply_text(
            "❌ No TTS keys configured.\n"
            "Copy `voiceenv.example` → `.voiceenv` and add ELEVENLABS_API_KEY or OPENAI_TTS_KEY."
        )
        return
    if len(TTS_REGISTRY) == 1:
        state.tts_enabled  = not state.tts_enabled
        state.tts_provider = next(iter(TTS_REGISTRY))
        state.save_current()
        status = f"🔊 ON ({state.tts_provider})" if state.tts_enabled else "🔊 OFF"
        await update.message.reply_text(f"TTS: {status}")
        return
    keyboard = []
    for prov in TTS_REGISTRY:
        active = "✓ " if (state.tts_enabled and state.tts_provider == prov) else ""
        keyboard.append([InlineKeyboardButton(f"{active}🔊 {prov}", callback_data=f"tts:{prov}")])
    if state.tts_enabled:
        keyboard.append([InlineKeyboardButton("❌ Disable TTS", callback_data="tts:__off__")])
    status = f"active: {state.tts_provider}" if state.tts_enabled else "disabled"
    await update.message.reply_text(
        f"🔊 TTS — {status}\nSelect provider:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ── Callback handlers ──────────────────────────────────────────────────────────

async def provider_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    payload  = query.data.split(":", 2)
    provider = payload[1]
    page     = int(payload[2]) if len(payload) > 2 else 0
    if provider == "__back__":
        return await _show_providers(query)
    if provider == "__fav__":
        return await _show_favorites_page(query, page)
    await _show_model_page(query, provider, page, fav_edit=False)


async def fav_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    payload  = query.data.split(":", 2)
    await _show_model_page(query, payload[1], int(payload[2]) if len(payload) > 2 else 0, fav_edit=True)


async def fav_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("fav:rm:"):
        full_key = query.data.split(":", 2)[2]
        if full_key in state.favorites:
            state.favorites.remove(full_key)
            state.save_favorites()
        return await _show_favorites_page(query, 0, removing=True)
    parts = query.data.split(":", 3)
    if len(parts) == 4:
        _, provider, page_str, model_name = parts
        state.toggle_favorite(f"{provider}/{model_name}")
        await _show_model_page(query, provider, int(page_str), fav_edit=True)


async def favrm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    payload = query.data.split(":", 2)
    await _show_favorites_page(query, int(payload[2]) if len(payload) > 2 else 0, removing=True)


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state.current_model = query.data.split(":", 1)[1]
    state.save_current()
    await query.edit_message_text(f"✅ Switched to: `{state.current_model}`", parse_mode="Markdown")


async def load_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filename = query.data.split(":", 1)[1]
    try:
        with open(CONVERSATIONS_DIR / filename) as f:
            data = json.load(f)
        state.conversation  = data.get("messages", [])
        state.current_model = data.get("model", state.current_model)
        state.settings      = data.get("settings", DEFAULT_SETTINGS.copy())
        state.save_current()
        await query.edit_message_text(
            f"✅ Loaded: {data.get('name')}\n({len(state.conversation)} messages)\nModel: `{state.current_model}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Error loading: {e}")


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 2)
    _, key = parts[0], parts[1]
    value  = parts[2] if len(parts) > 2 else ""
    if key == "thinking":
        state.settings["thinking"]    = None if value == "default" else value
    elif key == "temp":
        state.settings["temperature"] = None if value == "default" else float(value)
    elif key == "tokens":
        state.settings["max_tokens"]  = None if value == "default" else int(value)
    elif key == "parallel":
        state.parallel_tool_calls = not state.parallel_tool_calls
    elif key == "keyidx":
        prov = state.current_model.split("/")[0] if "/" in state.current_model else state.current_model
        keys = _current_provider_keys(prov)
        try:
            idx = int(value)
        except ValueError:
            idx = -1
        if prov in KEY_SWITCHABLE_PROVIDERS and 0 <= idx < len(keys):
            KEY_INDEX[prov] = idx
        state.save_current()
        text, markup = _build_settings_view()
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        return
    elif key == "fallback":
        if value == "clear":
            state.fallback_model = ""
            state.save_current()
            await query.edit_message_text("✅ Fallback model cleared.", parse_mode="Markdown")
            return
        elif value == "pick":
            # Open provider picker in fallback-selection mode
            keyboard = []
            for prov in sorted(MODEL_REGISTRY.keys()):
                keyboard.append([InlineKeyboardButton(f"⚪ {prov}", callback_data=f"fbprov:{prov}:0")])
            await query.edit_message_text(
                "Select provider for fallback model:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return
    state.save_current()
    parallel_status = "ON ✅" if state.parallel_tool_calls else "OFF ❌"
    await query.edit_message_text(
        f"✅ Updated {key} → {value}\n\n"
        f"*Current Settings:*\n"
        f"Thinking: {_fmt(state.settings['thinking'])}\n"
        f"Temperature: {_fmt(state.settings['temperature'])}\n"
        f"Max Tokens: {_fmt(state.settings['max_tokens'])}\n"
        f"Parallel tool calls: {parallel_status}\n"
        f"Fallback model: {state.fallback_model or '—'}",
        parse_mode="Markdown",
    )


async def websearch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    provider = query.data.split(":", 1)[1]
    if provider == "__off__":
        state.search_enabled = False
        state.save_current()
        await query.edit_message_text("🔍 Web search disabled")
        return
    if provider == "__rag__":
        state.search_rag_mode = not state.search_rag_mode
        state.save_current()
        mode = "RAG inject" if state.search_rag_mode else "tool calling"
        await query.edit_message_text(f"🔍 Search mode: {mode}")
        return
    state.search_enabled  = True
    state.search_provider = provider
    state.save_current()
    mode = "RAG" if state.search_rag_mode else "tool calling"
    await query.edit_message_text(f"🔍 Web search enabled: {provider} [{mode}]")


async def imageset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    provider = query.data.split(":", 1)[1]
    state.image_provider = provider
    state.save_current()
    await query.edit_message_text(
        f"🎨 Image provider set to: *{provider}*\n\nUse `/imagine <description>` to generate.",
        parse_mode="Markdown",
    )


async def vidset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    provider = query.data.split(":", 1)[1]
    state.video_provider = provider
    state.save_current()
    await query.edit_message_text(
        f"🎬 Video provider set to: *{provider}*\n\nUse `/video <description>` to generate.",
        parse_mode="Markdown",
    )


async def tts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    provider = query.data.split(":", 1)[1]
    if provider == "__off__":
        state.tts_enabled = False
        state.save_current()
        await query.edit_message_text("🔊 TTS disabled")
        return
    state.tts_enabled  = True
    state.tts_provider = provider
    state.save_current()
    await query.edit_message_text(f"🔊 TTS enabled: {provider}")


async def fbprov_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback model — provider selection."""
    query    = update.callback_query
    await query.answer()
    payload  = query.data.split(":", 2)
    provider = payload[1]
    page     = int(payload[2]) if len(payload) > 2 else 0
    models   = MODEL_REGISTRY.get(provider, [])
    if not models:
        await query.edit_message_text(f"❌ No models for {provider}")
        return
    total = len(models)
    start = page * MODELS_PER_PAGE
    end   = min(start + MODELS_PER_PAGE, total)
    keyboard = []
    for m in models[start:end]:
        full_key = f"{provider}/{m}"
        current  = "✓ " if full_key == state.fallback_model else ""
        cb = f"fbmodel:{full_key}"
        if len(cb.encode()) <= 64:
            keyboard.append([InlineKeyboardButton(f"{current}{m}", callback_data=cb)])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"fbprov:{provider}:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"fbprov:{provider}:{page+1}"))
    if nav:
        keyboard.append(nav)
    pages_total = (total + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE
    await query.edit_message_text(
        f"*{provider}* — select fallback model (page {page+1}/{pages_total}):",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
    )


async def fbmodel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback model — model selected."""
    query = update.callback_query
    await query.answer()
    state.fallback_model = query.data.split(":", 1)[1]
    state.save_current()
    await query.edit_message_text(
        f"✅ Fallback model set to: `{state.fallback_model}`", parse_mode="Markdown"
    )

# ── Voice message handler ──────────────────────────────────────────────────────

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TRANSCRIPTION_REGISTRY
    TRANSCRIPTION_REGISTRY = build_transcription_registry()
    if not TRANSCRIPTION_REGISTRY:
        await update.message.reply_text(
            "❌ No transcription keys configured.\n"
            "Copy `voiceenv.example` → `.voiceenv` and add WHISPER_API_KEY or GEMINI_VOICE_KEY."
        )
        return

    voice      = update.message.voice
    tg_file    = await context.bot.get_file(voice.file_id)
    audio_data = bytes(await tg_file.download_as_bytearray())

    await update.message.chat.send_action("typing")
    provider = state.transcription_provider or next(iter(TRANSCRIPTION_REGISTRY))
    text     = await call_transcription(provider, audio_data)

    if not text:
        await update.message.reply_text("❌ Transcription failed")
        return

    await update.message.reply_text(f"🎤 _{text}_", parse_mode="Markdown")

    # Process transcribed text through normal LLM flow
    state.add_message("user", text)
    await update.message.chat.send_action("typing")

    search_provider = state.search_provider if state.search_enabled else None
    image_provider  = state.image_provider  if IMAGE_REGISTRY       else None
    side_effects: list = []

    response = await call_llm(
        state.current_model, state.conversation, state.settings,
        search_provider, image_provider, side_effects,
    )
    state.add_message("assistant", response)

    await _handle_side_effects(update, side_effects)

    await _send_response(update, response)

# ── Photo handler (vision analysis) ───────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo    = update.message.photo[-1]  # largest available size
    tg_file  = await context.bot.get_file(photo.file_id)
    img_data = bytes(await tg_file.download_as_bytearray())
    caption  = update.message.caption or "Describe this image in detail."

    b64     = base64.b64encode(img_data).decode()
    content = [
        {"type": "text",      "text": caption},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
    ]
    state.add_message("user", content)
    await update.message.chat.send_action("typing")

    search_provider = state.search_provider if state.search_enabled else None
    image_provider  = state.image_provider  if IMAGE_REGISTRY       else None
    side_effects: list = []

    response = await call_llm(
        state.current_model, state.conversation, state.settings,
        search_provider, image_provider, side_effects,
    )
    state.add_message("assistant", response)

    await _handle_side_effects(update, side_effects)

    await _send_response(update, response)


# ── Document / file handler (analysis) ────────────────────────────────────────

_IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_TEXT_EXTS   = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", ".log", ".py", ".sh"}

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc      = update.message.document
    caption  = update.message.caption or ""
    mime     = doc.mime_type or ""
    fname    = doc.file_name or "file"
    ext      = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""

    tg_file   = await context.bot.get_file(doc.file_id)
    file_data = bytes(await tg_file.download_as_bytearray())

    await update.message.chat.send_action("typing")

    # ── Images sent as documents ───────────────────────────────────────────────
    if mime in _IMAGE_MIMES:
        b64     = base64.b64encode(file_data).decode()
        prompt  = caption or "Describe this image in detail."
        content = [
            {"type": "text",      "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]

    # ── PDFs — Claude native; other providers: unsupported ────────────────────
    elif mime == "application/pdf" or ext == ".pdf":
        if not state.current_model.startswith("anthropic/"):
            await update.message.reply_text(
                "⚠️ PDF analysis requires a Claude model. Switch with /models."
            )
            return
        b64     = base64.b64encode(file_data).decode()
        prompt  = caption or "Analyse this document and summarise its contents."
        content = [
            {"type": "text", "text": prompt},
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
        ]

    # ── Plain-text files ───────────────────────────────────────────────────────
    elif ext in _TEXT_EXTS or mime.startswith("text/"):
        try:
            text = file_data.decode("utf-8", errors="replace")
        except Exception:
            text = file_data.decode("latin-1", errors="replace")
        prompt  = caption or f"Analyse the following file ({fname}):"
        content = f"{prompt}\n\n```\n{text}\n```"

    else:
        await update.message.reply_text(
            f"⚠️ Unsupported file type: `{mime or ext}`\n"
            "Supported: images, PDFs (Claude only), text/code files.",
            parse_mode="Markdown",
        )
        return

    state.add_message("user", content)

    search_provider = state.search_provider if state.search_enabled else None
    image_provider  = state.image_provider  if IMAGE_REGISTRY       else None
    side_effects: list = []

    response = await call_llm(
        state.current_model, state.conversation, state.settings,
        search_provider, image_provider, side_effects,
    )
    state.add_message("assistant", response)

    await _handle_side_effects(update, side_effects)

    await _send_response(update, response)


# ── Free-text handler ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    if context.user_data.get("awaiting_save_name"):
        context.user_data["awaiting_save_name"] = False
        context.args = user_msg.split()
        await save_cmd(update, context)
        return

    state.add_message("user", user_msg)
    await update.message.chat.send_action("typing")

    search_provider = state.search_provider if state.search_enabled else None
    image_provider  = state.image_provider  if IMAGE_REGISTRY       else None
    side_effects: list = []

    response = await call_llm(
        state.current_model, state.conversation, state.settings,
        search_provider, image_provider, side_effects,
    )
    state.add_message("assistant", response)

    await _handle_side_effects(update, side_effects)

    await _send_response(update, response)


FREE_TEXT_HANDLER = handle_message

# ── Plugin entry point ─────────────────────────────────────────────────────────

def register(app: Application):
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    app.add_handler(CommandHandler("models",          models_cmd))
    app.add_handler(CommandHandler("fav",             fav_cmd))
    app.add_handler(CommandHandler("newconversation", newconversation_cmd))
    app.add_handler(CommandHandler("save",            save_cmd))
    app.add_handler(CommandHandler("load",            load_cmd))
    app.add_handler(CommandHandler("settings",        settings_cmd))
    app.add_handler(CommandHandler("status",          status_cmd))
    app.add_handler(CommandHandler("search",          search_cmd))
    app.add_handler(CommandHandler("websearch",       websearch_cmd))
    app.add_handler(CommandHandler("imagine",         imagine_cmd))
    app.add_handler(CommandHandler("video",           video_cmd))
    app.add_handler(CommandHandler("tts",             tts_cmd))
    app.add_handler(MessageHandler(filters.PHOTO,              handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL,       handle_document))
    app.add_handler(MessageHandler(filters.VOICE,              handle_voice))
    app.add_handler(CallbackQueryHandler(provider_callback,  pattern=r"^prov:"))
    app.add_handler(CallbackQueryHandler(fav_callback,       pattern=r"^fav:"))
    app.add_handler(CallbackQueryHandler(favrm_callback,     pattern=r"^favrm:"))
    app.add_handler(CallbackQueryHandler(fav_edit_callback,  pattern=r"^faved:"))
    app.add_handler(CallbackQueryHandler(model_callback,     pattern=r"^model:"))
    app.add_handler(CallbackQueryHandler(load_callback,      pattern=r"^load:"))
    app.add_handler(CallbackQueryHandler(settings_callback,  pattern=r"^set:"))
    app.add_handler(CallbackQueryHandler(websearch_callback, pattern=r"^ws:"))
    app.add_handler(CallbackQueryHandler(imageset_callback,  pattern=r"^imgset:"))
    app.add_handler(CallbackQueryHandler(vidset_callback,    pattern=r"^vidset:"))
    app.add_handler(CallbackQueryHandler(tts_callback,       pattern=r"^tts:"))
    app.add_handler(CallbackQueryHandler(fbprov_callback,    pattern=r"^fbprov:"))
    app.add_handler(CallbackQueryHandler(fbmodel_callback,   pattern=r"^fbmodel:"))
