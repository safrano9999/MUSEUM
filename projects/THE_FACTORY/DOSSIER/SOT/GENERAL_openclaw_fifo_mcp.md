# OpenClaw FIFO Interface

## Konzept

OpenClaw unterstützt stdin-Input via FIFO (Named Pipe).
Das ist der Schlüssel für die Schnittstelle zwischen Container-Apps und OpenClaw.

## Einmalig anlegen

```bash
mkfifo input.fifo
```

## OpenClaw beim Start drauf zeigen

```bash
openclaw --mcp < input.fifo
```

## Von beliebiger App reinschreiben

```bash
echo '...' > input.fifo
```

## Relevanz für Multi-App-Container

Jede Flask-App im Container kann direkt in die FIFO schreiben.
Kein HTTP-Umweg nötig — einfach `echo '...' > input.fifo` aus jedem Skript oder jeder App.

Das macht OpenClaw zur natürlichen Steuerzentrale für den Container:

- Flask-App schreibt Event/Befehl → FIFO
- OpenClaw empfängt → verarbeitet → reagiert (Telegram, Logs, etc.)

## Integration mit CLAWBRIDGE

FIFO-Pattern passt gut zu CLAWBRIDGE (inotify file-bus).
Mögliche Kombination:
- Apps schreiben in FIFO → OpenClaw
- oder Apps droppen Dateien in TRIGGERDIR → CLAWBRIDGE

## Protokoll

**MCP JSON** — OpenClaw liest MCP-konforme JSON-Messages aus der FIFO.

```bash
echo '{"method": "tools/call", "params": {"name": "send_message", "arguments": {"text": "Hello"}}}' > input.fifo
```

Jede App schreibt valides MCP JSON → OpenClaw verarbeitet als würde es über stdin von einem MCP-Client kommen.

## Nächste Schritte

- [ ] FIFO-Pfad im Container definieren (z.B. `/app/ipc/openclaw.fifo`)
- [ ] OpenClaw-Startskript anpassen
- [ ] Flask-Apps mit FIFO-Writer ausstatten (MCP JSON format)
- [ ] MCP-Schema dokumentieren: welche Tools/Methods unterstützt OpenClaw
