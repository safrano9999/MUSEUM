# PV D-A-CH – Missionsdossier

## A. SOLLZUSTAND
Ein eigenständiges Python-Skript (inkl. venv-Dependencies), das per Argument eine PLZ annimmt, dann:
1. alle relevanten Adress-/Gebäudedaten aus der OSM/Overpass API lädt,
2. anschließend sequenziell Vision-Toolcalls (LiteLLM) für Dach-/PV-/Schatten-Analyse ausführt,
3. und die Ergebnisse strukturiert in MariaDB schreibt (keine Dubletten, Upserts).

## B. Health Check & UI

**Projekt-Typ**: CLI-Tool

**Implementierung**: Python (mit `requests` für OSM/Imagery, `liteLLM` für Vision-Toolcalls, `sqlalchemy` für DB-Zugriff)

Zu Beginn prüft das Skript die DB-Verbindung (gemäß `.env`). Klappt das, zeigt es einen grünen ✔️ und legt – falls noch nicht vorhanden – die Basistabelle `pv_dach` an. Beim ersten Lauf werden dabei auch die fünf Zusatzspalten (`pv_absent_percent`, `roof_surface_count`, `dominant_orientation`, `shading_score`, `sat_image_blob`) erzeugt und bei späteren Läufen automatisch ergänzt, falls sie fehlen. Schlägt der Health-Check fehl, gibt es einen roten Hinweis + Exitcode.

- **Ohne Argumente**: zeigt Statistiken (Anzahl Adresspunkte, Fertig vs. offen) und arbeitet die komplette Queue A→Z ab.
- `--plz <xxxx>`: beschränkt Import/Vision auf eine bestimmte PLZ (inkl. Stats + optionalem Export).
- `--export [--plz <xxxx>]`: liefert CSV mit den relevanten Feldern (entweder global oder für eine PLZ).
- `--stats-only`: nur Statusbericht ohne Verarbeitung.
- `--osm-only`: führt nur den OSM-Import aus (kein Imagery/Vision), ideal für schnelle Tests.
- `--yard`: speichert zusätzlich den jeweiligen Satellitenbild-Ausschnitt als BLOB in MariaDB.
- `--help`: gibt genau diese CLI-Doku (Modi, Flags, Beispiele) aus.

Standardverhalten: das Skript setzt automatisch dort fort, wo es zuletzt aufgehört hat (Resume ist Default). Intern läuft dabei trotzdem die Kette OSM → Imagery → Vision → Feature → DB durch, QA/Reporting wird nur per Flag (`--export`, `--qa-sample`) ausgelöst.

## C. Dependencies
- **MariaDB/MySQL** mit Zugang auf die `pv_dach`-DB (Schema wird automatisch erweitert).
- **Python 3.11+** samt `venv` mit Packages wie `requests`, `pandas`, `shapely`, `liteLLM`, `opencv`, `pillow`, `sqlalchemy`, `pymysql`, `pyyaml`.
- **System-Tools** je nach Vision/Imagery (z. B. GDAL, libvips, ffmpeg) – werden bei Bedarf im README ergänzt.

## D. Artefakte, Dateien & Libraries
- `pv_dach.py`: Hauptskript (CLI).
- `.PV_D-A-CHenv`: enthält API-Tokens (OSM, Vision/LiteLLM, Tile-Provider) + Modellfallbacks.
- `pv_dach.toml`: technische Parameter (URLs, Provider, Thresholds, Exportfelder, Scheduler-Werte).
- `venv/requirements`: Python-Dependencies (z. B. `requests`, `pandas`, `shapely`, `liteLLM`, `opencv`, `pillow`, `sqlalchemy`).

## E. Peripherie
- Tabelle `pv_dach` nimmt den vollständigen OSM-Datensatz auf (inkl. Original-Timestamps).
- Pflichtspalten: `plz`, `address_id`, `osm_timestamp`, `vision_timestamp`, `status`.
- Zusätzliche Felder:
  - `pv_absent_percent` (FLOAT) – Wahrscheinlichkeit, dass keine PV-Anlage auf dem Dach installiert ist.
  - `roof_surface_count` (INT) – Anzahl Dachflächen pro Adresspunkt.
  - `dominant_orientation` (VARCHAR) – Himmelsrichtung der größten Dachfläche.
  - `shading_score` (FLOAT) – negativer Beschattungswert.
  - `sat_image_blob` (MEDIUMBLOB) – optionales Satellitenbild-Thumbnail (nur bei `--yard`).

## F. Research & Preparation

### Offene Research-Tasks
- **Blackbox Vision Toolcall**: PV-spezifische Vision-Modelle via LiteLLM evaluieren (Input/Output-Formate, Kosten, Rate-Limits, Prompt-Patterns). Deep Dive erlaubt; Grok kann unbegrenzt Tokens verbraten.
- **Evaluation Single vs. Multi-Agent**: Langfristig reines Skript oder koordinierte Bots?
- **DB-Setup & `.PV_D-A-CHenv`**: Zugangsdaten + Datenbank anlegen.

### Ideen & Weiteres

- Eigene hochauflösende kostenlose Bilder aus QGIS verwenden statt Satelliten-Imagery (Ressourcenschonung)?
  - **Bild 1**: Overlay mit Haus-Objekten & Dach-Konturen (Visualisierung für User)
  - **Bild 2**: Plain Raster ohne Overlays (saubere Grundlage für Vision-Auswertung)



