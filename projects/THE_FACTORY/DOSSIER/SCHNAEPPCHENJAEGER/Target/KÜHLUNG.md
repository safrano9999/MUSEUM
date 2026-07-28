# 🌡️ Kühlung

**Ziel:** 2x GPU + Hochleistungs-CPU kühlen, leise bleiben
**Recherche-Datum:** 2026-03-01

---

## 🖥️ CPU-Kühlung

### Empfehlung: Noctua NH-D15S (Luft)

| Spec | Wert |
|------|------|
| Typ | Dual-Tower Luftkühler |
| TDP | bis 250W |
| Lüfter | 2x 140mm |
| Höhe | 165mm |
| Lautstärke | extrem leise |

**Preis:** ~100–120€

**Pro:**
- ✅ Beste Luft-Kühlung überhaupt
- ✅ Ultra-leise
- ✅ Keine Pumpe = nichts kaputt
- ✅ 6 Jahre Garantie
- ✅ Kein Wartungsaufwand

**Contra:**
- ❌ Groß (RAM Kompatibilität prüfen!)
- ❌ Schwer (~1,2kg)

**Links:**
- https://noctua.at/de/nh-d15s

---

### Alternative: AIO 360mm Wasserkühlung

**Empfehlung:** ARCTIC Liquid Freezer III 360 ARGB

**Preis:** ~120–150€

**Pro:**
- ✅ Besser bei Dauerlast
- ✅ Mehr RAM-Clearance
- ✅ Sieht schicker aus

**Contra:**
- ❌ Pumpe kann ausfallen
- ❌ Wartung (alle 3–5 Jahre befüllen)
- ❌ Montage komplexer

**Links:**
- https://www.arctic.de/liquid-freezer-iii-360/ACFRE00137A

---

## 🌬️ Case-Lüfter

Bei Dual GPU Setup ist Airflow entscheidend!

### Empfehlung: Noctua NF-A14 PWM (140mm)

**Preis:** ~25–30€ pro Stück

**Minimale Lüfter-Konfiguration:**
```
Vorne:  3x 140mm (Intake) ←
Hinten: 1x 140mm (Exhaust) →
Oben:   3x 140mm (Exhaust) ↑
─────────────────────────
Total:  7 Lüfter empfohlen
Kosten: ~175–210€
```

**Links:**
- https://noctua.at/de/nf-a14-pwm

---

## 🎮 GPU-Kühlung

GPUs haben eigene Kühlung — aber man kann verbessern:

### Option: Aftermarket Kühler

**Arctic Accelero Xtreme IV** für RTX 4090
- Deutlich leiser als Werks-Kühler
- Bessere Temperaturen
- ~80–100€ pro GPU

**Wichtig:** Aftermarket GPU-Kühler können Garantie
der Karte verlieren → abwägen!

---

## 🌡️ Thermische Ziele

```
CPU Idle:     <40°C
CPU Last:     <80°C
GPU Idle:     <50°C
GPU Last:     <85°C (Throttling bei 90°C+)
```

**Tipp:** GPU Undervolting bei 4090 möglich
→ 15–20% weniger Strom, nur 5% weniger Performance
→ Deutlich kühlere und leisere Karte!
