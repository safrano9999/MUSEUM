# 🎮 GPU - Grafikkarte

**Ziel:** 2x GPU mit je 24GB VRAM für AI/ML Workloads
**Recherche-Datum:** 2026-03-01

---

## 🏆 Empfehlung #1: NVIDIA RTX 4090 (×2)

| Spec | Wert |
|------|------|
| VRAM | 24 GB GDDR6X |
| TDP | 450W |
| Architektur | Ada Lovelace |
| CUDA Cores | 16.384 |
| Memory Bandwidth | 1.008 GB/s |
| PCIe | 4.0 x16 |

**Preis:** ~1.600–2.200€ pro Karte (Stand März 2026)
**Total für 2x:** ~3.200–4.400€

**Pro:**
- ✅ Beste CUDA-Performance (NVIDIA-Ökosystem = besser für AI/ML)
- ✅ 24GB VRAM pro Karte = 48GB gesamt
- ✅ DLSS 3, beste Treiber-Unterstützung
- ✅ NVLink auf manchen Boards möglich

**Contra:**
- ❌ Sehr teuer
- ❌ 450W TDP × 2 = 900W nur GPU
- ❌ Braucht starkes Netzteil + gute Kühlung

**Links:**
- https://www.nvidia.com/de-de/geforce/graphics-cards/40-series/rtx-4090/
- https://geizhals.eu/?cat=gcard_video&xf=10444_24576
- https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html

---

## 🥈 Alternative: AMD RX 7900 XTX (×2)

| Spec | Wert |
|------|------|
| VRAM | 24 GB GDDR6 |
| TDP | 355W |
| Architektur | RDNA 3 |
| Memory Bandwidth | 960 GB/s |
| PCIe | 4.0 x16 |

**Preis:** ~850–1.000€ pro Karte (Stand März 2026)
**Total für 2x:** ~1.700–2.000€

**Pro:**
- ✅ Deutlich günstiger (fast halb so teuer)
- ✅ Bessere VRAM/€ Ratio
- ✅ Geringerer Stromverbrauch
- ✅ Open Source ROCm für ML

**Contra:**
- ❌ ROCm schwächer als CUDA
- ❌ Manche ML-Frameworks nur für NVIDIA optimiert

**Links:**
- https://www.amd.com/de/products/graphics/desktops/radeon/7000/amd-radeon-rx-7900-xtx.html
- https://geizhals.eu/?cat=gcard_video&xf=10444_24576~10452_7900+XTX

---

## ⚠️ Dual-GPU Wichtig

- Beide GPUs brauchen x8/x8 oder x16/x16 (nicht x16/x4!)
- Mindestens 3 Slots Abstand zwischen GPUs für Kühlung
- RTX 4090 Triple-Slot beachten

---

## 🔮 Ausblick

- RTX 5090: ~28GB VRAM (2026) — noch teuer, Preise für 4090 könnten fallen
