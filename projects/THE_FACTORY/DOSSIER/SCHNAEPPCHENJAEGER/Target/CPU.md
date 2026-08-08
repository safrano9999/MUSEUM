# 🧠 CPU - Prozessor

**Ziel:** Schnelle CPU für AI/ML Workloads + Dual GPU
**Recherche-Datum:** 2026-03-01

---

## 🏆 Empfehlung: AMD Ryzen 9 9950X

| Spec | Wert |
|------|------|
| Kerne | 16 Kerne / 32 Threads |
| Takt | 4.3 GHz Base / 5.7 GHz Boost |
| Cache | 64MB L3 Cache |
| TDP | 170W |
| Sockel | AM5 |
| Fertigung | TSMC 4nm |
| RAM | DDR5-5600 offiziell |

**Preis:** ~600–700€ (Stand März 2026)

**Pro:**
- ✅ 16 Kerne ideal für AI Workloads (Parallelisierung)
- ✅ Sehr schnell bei Single-Thread
- ✅ AM5 Plattform → langfristig
- ✅ Gut für CPU-Offloading (wenn GPU VRAM nicht reicht)

**Contra:**
- ❌ Teuer
- ❌ 170W TDP → braucht gute Kühlung
- ❌ Kein integrierter Grafikchip (bei Non-X Varianten)

**Links:**
- https://www.amd.com/de/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x.html
- https://geizhals.eu/?cat=cpu&xf=1628_Ryzen+9+9950X

---

## 🥈 Alternative: AMD Ryzen 9 7950X (günstiger)

| Spec | Wert |
|------|------|
| Kerne | 16 Kerne / 32 Threads |
| Takt | 4.5 GHz Base / 5.7 GHz Boost |
| Cache | 64MB L3 Cache |
| TDP | 170W |

**Preis:** ~400–500€ (gefallen durch 9950X Launch)

**Pro:**
- ✅ Deutlich günstiger als 9950X
- ✅ Fast gleiche Performance
- ✅ Gleiche AM5 Plattform

**Links:**
- https://geizhals.eu/?cat=cpu&xf=1628_Ryzen+9+7950X

---

## 🧮 Warum 16 Kerne für AI/ML?

```
LLM Inferenz (llama.cpp):
→ CPU-Threads für Quantisierung
→ 16 Kerne = deutlich schneller als 8 Kerne

LLM Training:
→ Datenpipeline läuft auf CPU
→ Mehr Kerne = weniger Bottleneck

CPU Offloading:
→ Wenn VRAM voll: Schichten auf RAM + CPU
→ Mehr Kerne = schnellere Verarbeitung
```

---

## 💡 Intel Alternative: Core i9-14900K

**Preis:** ~450–550€

- Schneller bei Single-Thread
- Schlechter bei Multithread vs Ryzen
- LGA1700 (ältere Platform, keine Zukunft)
- **Empfehle AMD** für Workstation-Builds
