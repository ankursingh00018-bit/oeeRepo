# Document 5 — Quality Troubleshooting SOP (Fleet-wide)

Purpose: Connects machine health signals to product quality outcomes,
so the Agent's reasoning is not just "the machine is vibrating" but
"machine health is affecting production and product quality."

## 1. General Reject Rate Bands

| Band | Reject Rate | Meaning |
|---|---|---|
| Normal | <2.0% | No action needed |
| Watch | 2.0–4.0% | Monitor trend |
| Investigation Required | >4.0% | Trigger diagnostic sequence |

Machine-specific bands override the general table where defined below.

## 2. Machine-Specific Quality Thresholds

- **M-101 (CNC Lathe):** Normal <2.0%, Investigation >4.0%. Common
  quality issue: dimensional variation in shaft diameter/roundness.
- **M-102 (CNC Milling):** Normal <2.0%, Investigation >4.0%. Common
  quality issue: dimensional variation, surface finish defects.
- **M-103 (Robotic Welding Cell):** Normal <1.5%, Investigation >3.5%
  (tighter band — weld defects are structurally significant). Common
  quality issue: porosity, incomplete fusion, weld spatter.
- **M-104 (Injection Molding):** Normal <2.5%, Investigation >5.0%.
  Common quality issues: short shots, flash, sink marks, warping.
- **M-105 (Hydraulic Press):** Normal <1.8%, Investigation >3.5%.
  Common quality issues: burrs, cracking, dimensional deviation from
  die wear or misalignment.

## 3. Defect-to-Cause Correlation Table

| Symptom | Likely Process Cause | Likely Mechanical Cause |
|---|---|---|
| Dimensional variation (M-101, M-102) | Tool wear, feed rate drift | Spindle bearing wear, vibration |
| Surface finish defects (M-102) | Coolant contamination, wrong feed/speed | Tool imbalance, spindle vibration |
| Weld porosity (M-103) | Shielding gas flow low, contamination | — |
| Incomplete fusion (M-103) | Wire feed tension fault, travel speed too high | Joint servo instability |
| Short shots (M-104) | Barrel temperature low, injection pressure low | — |
| Flash (M-104) | Clamp force insufficient, mold wear | — |
| Burrs / cracking (M-105) | Die wear, material thickness variation | Die misalignment, ram vibration |

## 4. Correlation Logic for the Agent

Treat these signals as compounding evidence, not independent facts:

```
High vibration
       +
High temperature
       +
High reject rate
       +
Production rate loss
       =
Strong evidence of a mechanical (not process-parameter) root cause
```

Conversely:

```
Normal vibration
       +
Rising reject rate
       +
Specific defect type (e.g., short shots, flash)
       =
Investigate process parameters first (temperature, pressure, feed),
not mechanical wear
```

## 5. Production Rate Correlation

Production rate dropping alongside reject rate rising (rather than
reject rate rising with production rate steady) suggests the machine
is being slowed or stopped by its own control system in response to
degrading conditions — this is itself evidence supporting a HIGH
severity classification, since the PLC/control system is already
reacting defensively.
