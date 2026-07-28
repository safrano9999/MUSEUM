# OPENCLAW_CONTAINER

**Beschreibung**: Generisches OpenClaw Container-Setup (Podman) — sauberes Base-Image mit Python/pip-Layer, flexibel erweiterbar für alle Factory-Projekte.

---

## A. Sollzustand

- Podman-basiertes Container-Setup für OpenClaw
- Python 3 + pip im Image (nicht im Standard-Image enthalten)
- `requirements.txt` für flexible pip-Erweiterungen
- Bestehende `.openclaw/` Config mountbar
- Generisch nutzbar für alle THE_FACTORY Projekte
- ALL_LLMS als pip-Dependency vorinstalliert
- Einfacher Rebuild bei neuen Dependencies

---

## B. Health Check & UI

**Projekt-Typ**: Container-Image + Compose-Setup

**Implementierung**: Podman / Containerfile (OCI-kompatibel)

Beim Start: OpenClaw Gateway + CLI starten, Python-Umgebung prüfen, ALL_LLMS Registry bauen. Health-Check via `/healthz` Endpoint.

**Features**:
- `podman compose up` — Alles starten
- `podman compose exec openclaw pip install <package>` — On-the-fly pip installieren
- `podman compose build` — Rebuild mit neuen requirements.txt Einträgen
- Volume-Mounts für Config-Persistenz

**Standardverhalten**: OpenClaw Gateway auf Port 18789, Python-ready.

---

## C. Dependencies

- Podman 5.x (vorhanden)
- OpenClaw Base-Image (`node:24-bookworm` basiert)
- Python 3.10+ (dazu installiert)
- pip + requirements.txt
- ALL_LLMS Package (Milestone 2)

---

## D. Artefakte, Dateien & Libraries

- `Containerfile` – Image-Definition (OpenClaw + Python + pip)
- `compose.yml` – Podman Compose Setup
- `requirements.txt` – Python Dependencies (ALL_LLMS + Projekt-spezifisches)
- `.env` – API-Keys + Config
- `docker-setup.sh` – Setup-Script (optional, angelehnt an offizielle Docs)

---

## E. Peripherie

```
Containerfile
  ↓
Base: OpenClaw (node:24-bookworm)
  + python3, python3-pip (apt)
  + requirements.txt (pip)
  + ALL_LLMS (pip install -e)
  ↓
compose.yml
  - openclaw-gateway (Port 18789)
  - Volumes: ~/.openclaw/ → /home/node/.openclaw/
  - Env: API-Keys, OPENCLAW_* Vars
  ↓
Runtime: OpenClaw + Python + alle LLM-Provider verfügbar
```

---

## F. Ideen & Weiteres

- Multi-Stage Build für kleineres Image
- Ollama als Sidecar-Container im Compose
- Auto-Rebuild Hook bei requirements.txt Änderung
- Dev-Container Config für VS Code / Claude Code
- GPU-Passthrough für lokale Models (Ollama)

---

## Z. Vom Architect auszufüllen

Bevor Übergabe an den Orchestrator:

- [x] **Single oder Multi-Agent?** (Step 0 Entscheidung)
  - [x] Single → Claude Code Workflow
  - [ ] Multi → Orchestrator mit Worker-Agents

- [x] **Blackbox Research abgeschlossen?**
  - OpenClaw Docker Docs analysiert (openclaws.io, docs.openclaw.ai)
  - Env-Vars und Volume-Struktur dokumentiert
  - Python nicht im Standard-Image → muss via apt dazu

- [x] **Datenquellen erreichbar & getestet?**
  - Podman 5.7.0 installiert
  - Bestehende Images vorhanden (pv-dach, qgis)
  - .openclaw/ Config vollständig

- [ ] **Entwicklungs-Setup fertig?**
  - Containerfile + compose.yml erstellen
  - Test-Build durchführen

- [ ] **Worker-Agent Strategie geklärt?**
  - N/A — Single-Agent

- [x] **Gibt es Milestones / Phasen?**
  - Phase 1: Base Containerfile (OpenClaw + Python + pip)
  - Phase 2: compose.yml + Volume-Mounts + Env
  - Phase 3: ALL_LLMS integrieren + requirements.txt Workflow
  - Phase 4: In bestehende Projekte einbinden (PV_D-A-CH, MAILSORT, etc.)
