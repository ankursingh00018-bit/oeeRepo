# Document 1 — Machine Manual (Fleet: M-101 to M-105)

Purpose: Defines each machine's identity, sensors, and operating thresholds
(Normal / Warning / Critical) used by the Agent for threshold analysis.
Every machine section below is self-contained and can be retrieved
independently by machine ID.

---

## Machine M-101 — CNC Lathe ("Lathe-1")

**Machine ID:** M-101
**Machine Type:** CNC Lathe
**Purpose:** Turns precision steel shafts and cylindrical components for
the drivetrain assembly line.

### Sensor Thresholds — M-101

| Sensor | Normal | Warning | Critical |
|---|---|---|---|
| Spindle Temperature (°C) | 35–70 | 70–82 | >82 |
| Vibration (mm/s) | 0–3.0 | 3.0–4.5 | >4.5 |
| Spindle Load (%) | 20–65 | 65–80 | >80 |
| Coolant Flow (L/min) | 8–14 | 5–8 | <5 |
| Reject Rate (%) | <2.0 | 2.0–4.0 | >4.0 |

**Escalation note:** Vibration >6.0 mm/s on M-101 triggers immediate
escalation regardless of other readings, due to shaft-bore precision
tolerances.

**Operating limits:** Max spindle speed 4,200 RPM. Max continuous run
without coolant check: 6 hours.

**Safety boundary:** Chuck guard interlock must remain closed above
1,000 RPM.

---

## Machine M-102 — CNC Milling Machine ("Mill-1")

**Machine ID:** M-102
**Machine Type:** CNC Milling Machine
**Purpose:** Produces precision aluminum components (housings, brackets)
requiring tight dimensional tolerance.

### Sensor Thresholds — M-102

| Sensor | Normal | Warning | Critical |
|---|---|---|---|
| Temperature (°C) | 40–75 | 75–85 | >85 |
| Vibration (mm/s) | 0–3.5 | 3.5–5.0 | >5.0 |
| Spindle Load (%) | 20–70 | 70–85 | >85 |
| Coolant Temperature (°C) | 15–30 | 30–38 | >38 |
| Reject Rate (%) | <2.0 | 2.0–4.0 | >4.0 |
| Production Rate (%) | >=90 | 80–90 | <80 |

**Escalation note:** Vibration >7.0 mm/s on M-102 requires immediate
escalation — this combination has historically correlated with spindle
bearing degradation on this unit (see Maintenance History, INC-1001,
INC-1058).

**Operating limits:** Max spindle speed 12,000 RPM. Rated aluminum
alloy: 6061-T6.

**Safety boundary:** Enclosure door interlock; spindle stops within
0.5s of door release.

---

## Machine M-103 — Robotic Welding Cell ("Weld-Cell-1")

**Machine ID:** M-103
**Machine Type:** 6-axis Robotic Welding Cell (MIG)
**Purpose:** Performs automated chassis welds for the frame subassembly.

### Sensor Thresholds — M-103

| Sensor | Normal | Warning | Critical |
|---|---|---|---|
| Joint-3 Servo Temperature (°C) | 30–65 | 65–78 | >78 |
| Joint Vibration (mm/s) | 0–2.5 | 2.5–4.0 | >4.0 |
| Wire Feed Tension (N) | 8–14 | 14–18 or 5–8 | >18 or <5 |
| Shielding Gas Flow (L/min) | 12–18 | 9–12 | <9 |
| Weld Reject Rate (%) | <1.5 | 1.5–3.5 | >3.5 |

**Escalation note:** Wire feed tension outside range combined with
rising weld reject rate indicates a feed mechanism problem, not a
servo/bearing problem — do not conflate the two failure families on
this machine.

**Operating limits:** Max joint speed 180°/s. Duty cycle: 70% at rated
current.

**Safety boundary:** Light curtain must be active during any cell
motion; robot faults to safe-stop on curtain breach.

---

## Machine M-104 — Injection Molding Machine ("Mold-1")

**Machine ID:** M-104
**Machine Type:** Injection Molding Machine (plastics)
**Purpose:** Molds plastic housings and enclosures from ABS/PC resin.

### Sensor Thresholds — M-104

| Sensor | Normal | Warning | Critical |
|---|---|---|---|
| Barrel Zone-2 Temperature (°C) | 200–230 | 230–245 | >245 |
| Hydraulic Pressure (bar) | 90–130 | 130–150 | >150 or <70 |
| Cycle Time Variance (%) | <5 | 5–12 | >12 |
| Screw Vibration (mm/s) | 0–2.0 | 2.0–3.2 | >3.2 |
| Reject Rate (%) | <2.5 | 2.5–5.0 | >5.0 |

**Escalation note:** Barrel temperature critical + reject rate rising
together typically indicates heater band failure, not mechanical wear —
see Quality Troubleshooting SOP for the short-shot/flash decision tree.

**Operating limits:** Max clamp force 850 kN. Resin dry time minimum:
4 hours before run.

**Safety boundary:** Nozzle guard interlock; platen safety gate must be
closed to build clamp pressure.

---

## Machine M-105 — Hydraulic Stamping Press ("Press-1")

**Machine ID:** M-105
**Machine Type:** Hydraulic Stamping Press
**Purpose:** Stamps sheet-metal brackets and panels from coil steel.

### Sensor Thresholds — M-105

| Sensor | Normal | Warning | Critical |
|---|---|---|---|
| Hydraulic Oil Temperature (°C) | 35–60 | 60–72 | >72 |
| Ram Vibration (mm/s) | 0–3.0 | 3.0–4.8 | >4.8 |
| Hydraulic Pressure (bar) | 180–220 | 220–240 | >240 or <150 |
| Die Alignment Deviation (mm) | 0–0.15 | 0.15–0.30 | >0.30 |
| Reject Rate (%) | <1.8 | 1.8–3.5 | >3.5 |

**Escalation note:** Die alignment deviation >0.30 mm combined with
rising reject rate requires immediate stop — continued operation risks
die damage, not just part rejects.

**Operating limits:** Max tonnage 400T. Stroke rate: up to 25 SPM.

**Safety boundary:** Two-hand anti-tie-down controls mandatory; light
curtain covers die area; press cannot cycle with curtain breached.

---

### Fleet-wide notes for the Agent

- Thresholds are machine-specific — never apply M-102's vibration
  thresholds to M-101, M-103, M-104, or M-105 or vice versa.
- "Critical" on any sensor is necessary but not sufficient for a root
  cause — always cross-reference PLC alarms, production/quality data,
  and maintenance history before naming a probable cause.
