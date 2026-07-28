# 💾 RAM - Arbeitsspeicher

**Ziel:** Schneller DDR5 für AI/ML Workstation mit Dual GPU
**Recherche-Datum:** 2026-03-01

---

## ⚠️ RAM-Preislage März 2026

RAM-Preise sind durch AI-Boom stark gestiegen!
- DDR5 64GB: ~700–900€
- DDR5 128GB: ~1.200–1.800€
- Preise erst 2027 voraussichtlich wieder stabiler

---

## 🏆 Empfehlung: 128GB DDR5 Kit

**Warum 128GB?**
- 2x 24GB GPU VRAM → Systemseitig braucht man Puffer
- AI/ML Modelle: LLaMA 70B benötigt 140GB gesamt (VRAM + RAM)
- Weniger ist ein Bottleneck

### Option A: G.Skill Trident Z5 128GB DDR5-6000

| Spec | Wert |
|------|------|
| Kapazität | 4x 32GB = 128GB |
| Geschwindigkeit | DDR5-6000 |
| Timings | CL30 |
| Form Factor | DIMM |

**Preis:** ~1.400–1.600€ (März 2026, AI-Preissurge)

**Links:**
- https://www.gskill.com/product/165/390/1637054418/F5-6000J3040G32GX2-TZ5RK
- https://geizhals.eu/?cat=ramddr5

### Option B: Corsair Dominator Platinum 64GB DDR5-6400 (Budget)

| Spec | Wert |
|------|------|
| Kapazität | 2x 32GB = 64GB |
| Geschwindigkeit | DDR5-6400 |
| Timings | CL32 |

**Preis:** ~700–900€

**Pro:** Günstiger Einstieg, später auf 128GB aufrüstbar
**Contra:** 64GB kann bei großen Modellen Engpass sein

**Links:**
- https://www.corsair.com/de/de/p/memory/cmt64gx5m2b6400c32/dominator-platinum-rgb-64gb--2x32gb--ddr5-dram-6400mhz-cl32

---

## 🧮 Warum DDR5-6000 optimal?

```
DDR5-6000 CL30 = bestes Preis/Performance-Verhältnis für AMD AM5
DDR5-6400+ = teurer, minimaler Gewinn
DDR5-5600 = günstiger, merklich langsamer
```

**AMD EXPO Profile nutzen** → automatisch optimale Timings

---

## 📊 RAM für AI/ML Planung

| Modell | VRAM benötigt | RAM benötigt |
|--------|---------------|--------------|
| LLaMA 7B | ~14GB | ~8GB |
| LLaMA 13B | ~26GB | ~16GB |
| LLaMA 70B | ~140GB | ~64GB+ |
| LLaMA 405B | ~810GB | Cluster nötig |

Mit 2x RTX 4090 (48GB VRAM) + 128GB RAM:
→ LLaMA 70B läuft via CPU offloading ✅
