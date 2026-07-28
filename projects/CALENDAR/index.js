import { spawn } from "node:child_process";
import fs from "node:fs";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const pluginRoot = path.resolve(fileURLToPath(new URL(".", import.meta.url)));
const defaultConfigPath = path.join(pluginRoot, "config.json");
const requirementsPath = path.join(pluginRoot, "requirements.txt");
const venvDir = path.join(pluginRoot, ".venv");
const venvPython = path.join(venvDir, "bin", "python");
const fetcherPath = path.join(pluginRoot, "calendar_fetch.py");
const defaultWebhookPath = "/plugins/calendar/run";

const configSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    configPath: { type: "string", description: "Optional plugin config.json path." },
    pythonPath: { type: "string", description: "Optional Python interpreter path." },
    calenvPath: { type: "string", description: "Path to .env with CALENDAR_* iCal entries." },
    envFile: { type: "string", description: "Compatibility alias for calenvPath." },
    logDir: { type: "string", description: "Directory for fetch logs." },
    certPath: { type: "string", description: "Optional CA certificate .pem path." },
    timezone: { type: "string", default: "Europe/Vienna" },
    emptyMessage: { type: "string", default: "📭 Keine Termine im Zeitfenster." },
    autoSetupPython: {
      type: "boolean",
      default: true,
      description: "Create .venv and install Python requirements on first run.",
    },
    webhook: {
      type: "object",
      additionalProperties: false,
      properties: {
        enabled: { type: "boolean", default: true },
        path: { type: "string", default: defaultWebhookPath },
      },
    },
    delivery: {
      type: "object",
      additionalProperties: false,
      description: "Optional direct outbound target for the webhook.",
      properties: {
        channel: { type: "string", default: "telegram" },
        target: { type: "string" },
        accountId: { type: "string" },
      },
    },
  },
};

const toolParameters = {
  type: "object",
  additionalProperties: false,
  properties: {},
};

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function readString(value) {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function expandHome(raw) {
  if (!raw.startsWith("~/")) {
    return raw;
  }
  return path.join(process.env.HOME ?? process.cwd(), raw.slice(2));
}

function resolvePath(rawPath, baseDir) {
  const expanded = expandHome(rawPath);
  return path.isAbsolute(expanded) ? expanded : path.resolve(baseDir, expanded);
}

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return {};
  }
}

function readPluginConfig(ctx) {
  if (isRecord(ctx?.pluginConfig)) {
    return ctx.pluginConfig;
  }
  const config = ctx.getRuntimeConfig?.() ?? ctx.runtimeConfig ?? ctx.config;
  const entries = isRecord(config?.plugins) && isRecord(config.plugins.entries)
    ? config.plugins.entries
    : undefined;
  const entry = isRecord(entries?.calendar) ? entries.calendar : undefined;
  return isRecord(entry?.config) ? entry.config : {};
}

function resolveConfigPath(ctx) {
  const cfg = readPluginConfig(ctx);
  const configured = readString(cfg.configPath) ?? readString(process.env.CALENDAR_CONFIG);
  return configured ? resolvePath(configured, pluginRoot) : defaultConfigPath;
}

function effectiveConfig(ctx) {
  const configPath = resolveConfigPath(ctx);
  return {
    ...readJson(configPath),
    ...readPluginConfig(ctx),
    configPath,
  };
}

function calendarPaths(ctx) {
  const cfg = effectiveConfig(ctx);
  const configDir = path.dirname(cfg.configPath);
  const calenvPath = resolvePath(
    readString(cfg.calenvPath) ?? readString(cfg.envFile) ?? ".env",
    configDir,
  );
  const logDir = resolvePath(readString(cfg.logDir) ?? "LOGS", configDir);
  const certPath = readString(cfg.certPath)
    ? resolvePath(cfg.certPath, configDir)
    : path.join(configDir, "certs", "cert.pem");
  return { cfg, calenvPath, logDir, certPath };
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: { ...process.env, PYTHONUNBUFFERED: "1", ...options.env },
      signal: options.signal,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = options.timeoutMs
      ? setTimeout(() => {
          timedOut = true;
          child.kill("SIGTERM");
        }, options.timeoutMs)
      : undefined;
    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr?.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", (error) => {
      if (timer) {
        clearTimeout(timer);
      }
      resolve({ code: -1, stdout, stderr: `${stderr}${error.message}`, timedOut });
    });
    child.on("close", (code) => {
      if (timer) {
        clearTimeout(timer);
      }
      resolve({ code: code ?? -1, stdout, stderr, timedOut });
    });
  });
}

async function setupPython(signal) {
  const create = await runProcess(
    readString(process.env.CALENDAR_BOOTSTRAP_PYTHON) ?? "python3",
    ["-m", "venv", venvDir],
    { cwd: pluginRoot, signal, timeoutMs: 120_000 },
  );
  if (create.code !== 0) {
    throw new Error(`CALENDAR Python venv setup failed: ${create.stderr || create.stdout}`);
  }
  const install = await runProcess(venvPython, ["-m", "pip", "install", "-r", requirementsPath], {
    cwd: pluginRoot,
    signal,
    timeoutMs: 300_000,
  });
  if (install.code !== 0) {
    throw new Error(`CALENDAR requirements install failed: ${install.stderr || install.stdout}`);
  }
}

async function resolvePython(ctx, signal) {
  const cfg = effectiveConfig(ctx);
  const configured = readString(cfg.pythonPath) ?? readString(process.env.CALENDAR_PYTHON);
  if (configured) {
    return expandHome(configured);
  }
  if (await exists(venvPython)) {
    return venvPython;
  }
  const autoSetup = cfg.autoSetupPython !== false || process.env.CALENDAR_AUTO_SETUP === "1";
  if (autoSetup) {
    await setupPython(signal);
    return venvPython;
  }
  return "python3";
}

async function runCalendar(ctx, signal) {
  const { cfg, calenvPath, logDir, certPath } = calendarPaths(ctx);
  if (!(await exists(fetcherPath))) {
    throw new Error(`CALENDAR fetcher not found: ${fetcherPath}`);
  }
  await mkdir(logDir, { recursive: true });

  const timezone = readString(cfg.timezone) ?? "Europe/Vienna";
  const emptyMessage = readString(cfg.emptyMessage) ?? "📭 Keine Termine im Zeitfenster.";
  const python = await resolvePython(ctx, signal);
  const certArg = fs.existsSync(certPath) ? certPath : "";

  const result = await runProcess(
    python,
    [
      fetcherPath,
      "--calenv",
      calenvPath,
      "--logdir",
      logDir,
      "--cert",
      certArg,
      "--timezone",
      timezone,
      "--past-hours",
      "1",
      "--days",
      "7",
    ],
    {
      cwd: pluginRoot,
      signal,
      timeoutMs: 120_000,
    },
  );

  if (result.code === 2) {
    return { ok: true, text: emptyMessage, empty: true };
  }
  if (result.code !== 0) {
    const tail = `${result.stderr}\n${result.stdout}`.trim().slice(-3000);
    throw new Error(tail || `CALENDAR exited with ${result.code}`);
  }
  return {
    ok: true,
    text: result.stdout.trim() || emptyMessage,
    empty: false,
  };
}

function createTool(ctx) {
  return {
    name: "calendar_run",
    label: "CALENDAR",
    displaySummary: "Show upcoming calendar events.",
    description: "Fetch configured iCal/Nextcloud calendars and show upcoming appointments.",
    parameters: toolParameters,
    async execute(_toolCallId, params, signal) {
      const payload = await runCalendar(ctx, signal);
      return {
        content: [{ type: "text", text: payload.text }],
        details: payload,
      };
    },
  };
}

async function deliverIfConfigured(api, text) {
  const cfg = effectiveConfig(api);
  const delivery = isRecord(cfg.delivery) ? cfg.delivery : {};
  const target = readString(delivery.target);
  if (!target) {
    return false;
  }
  const channel = readString(delivery.channel) ?? "telegram";
  const sendText = (await api.runtime.channel.outbound.loadAdapter(channel))?.sendText;
  if (!sendText) {
    throw new Error(`No outbound adapter configured for ${channel}.`);
  }
  await sendText({
    cfg: api.runtime.config?.current?.() ?? api.config,
    to: target,
    text,
    ...(readString(delivery.accountId) ? { accountId: delivery.accountId } : {}),
  });
  return true;
}

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(`${JSON.stringify(payload, null, 2)}\n`);
}

function registerWebhook(api) {
  const cfg = effectiveConfig(api);
  const webhook = isRecord(cfg.webhook) ? cfg.webhook : {};
  if (webhook.enabled === false) {
    return;
  }
  const routePath = readString(webhook.path) ?? defaultWebhookPath;
  api.registerHttpRoute({
    path: routePath,
    auth: "gateway",
    match: "exact",
    replaceExisting: true,
    async handler(req, res) {
      if (req.method !== "POST") {
        res.setHeader("Allow", "POST");
        sendJson(res, 405, { ok: false, error: "method_not_allowed" });
        return true;
      }
      try {
        const payload = await runCalendar(api);
        const delivered = await deliverIfConfigured(api, payload.text);
        sendJson(res, 200, { ...payload, delivered });
      } catch (error) {
        api.logger.error?.(`calendar webhook failed: ${error instanceof Error ? error.message : String(error)}`);
        sendJson(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) });
      }
      return true;
    },
  });
  api.logger.info?.(`calendar webhook registered at ${routePath}`);
}

export default definePluginEntry({
  id: "calendar",
  name: "CALENDAR",
  description: "Shows upcoming iCal/Nextcloud calendar events in Telegram.",
  configSchema,
  register(api) {
    api.registerTool((ctx) => createTool(ctx), { names: ["calendar_run"] });
    api.registerCommand({
      name: "calendar",
      description: "Show upcoming calendar appointments.",
      acceptsArgs: false,
      requireAuth: true,
      handler: async () => {
        const payload = await runCalendar(api);
        return { text: payload.text };
      },
    });
    registerWebhook(api);
  },
});
