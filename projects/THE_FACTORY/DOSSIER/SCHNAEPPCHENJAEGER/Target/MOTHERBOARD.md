# 🖥️ Motherboard

**Ziel:** Dual GPU (2x PCIe x16 oder x8/x8) mit AMD AM5 oder Intel LGA1700
**Recherche-Datum:** 2026-03-01

---

## 🏆 Empfehlung #1: MSI MPG X670E Carbon WIFI (AMD AM5)

| Spec | Wert |
|------|------|
| Sockel | AM5 (Ryzen 7000/9000) |
| Chipset | X670E |
| PCIe | 5.0 x8/x8 (dual GPU) |
| RAM | DDR5, 4 Slots, max 128GB |
| M.2 | 4x M.2 Slots |
| Form Factor | ATX |

**Preis:** ~350–450€ (Stand März 2026)

**Warum X670E für Dual GPU:**
- PCIe 5.0 x8/x8 = äquivalent zu PCIe 4.0 x16
- Kein Performance-Verlust gegenüber x16/x16

**Pro:**
- ✅ PCIe 5.0 x8/x8 ohne M.2-Verlust
- ✅ Beste Dual-GPU Unterstützung auf AM5
- ✅ Ryzen 9 7950X / 9950X kompatibel
- ✅ DDR5 Support

**Contra:**
- ❌ Teuer
- ❌ B650 reicht NICHT für Dual GPU (nur x16/x4)

**Links:**
- https://www.msi.com/Motherboard/MPG-X670E-CARBON-WIFI
- https://geizhals.eu/?cat=mbam4

---

## 🥈 Alternative: ASUS ProArt X670E-Creator WiFi

| Spec | Wert |
|------|------|
| Sockel | AM5 |
| Chipset | X670E |
| PCIe | 5.0 x8/x8 |
| RAM | DDR5, 4 Slots, max 128GB |

**Preis:** ~400–500€

**Pro:**
- ✅ Speziell für Creator/Workstation ausgelegt
- ✅ Sehr gute VRM-Kühlung
- ✅ Thunderbolt 4

**Links:**
- https://www.asus.com/motherboards-components/motherboards/proart/proart-x670e-creator-wifi/

---

## ⚠️ Wichtig: PCIe Konfiguration

```
X670E / X870E:  x8/x8  (PCIe 5.0) ✅ Empfohlen
B650:           x16/x4             ❌ Nicht gut für Dual GPU
Z790 (Intel):   x8/x8  (PCIe 4.0) ✅ Alternative
```

**Faustregel:** Immer prüfen ob beide Slots bei Dual-GPU-Nutzung
auf x8 oder höher bleiben!

---

## 🔮 Ausblick

- X870E Boards (neuere Generation) bereits verfügbar
- AMD AM5 bleibt langfristig → gute Investition
