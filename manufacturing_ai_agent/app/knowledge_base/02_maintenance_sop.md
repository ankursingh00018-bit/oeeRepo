# Document 2 — Maintenance SOP (Fleet-wide)

Purpose: Defines what maintenance (human or Agent) should do when an
abnormal condition is detected on any fleet machine (M-101 through
M-105). This SOP governs the Agent's diagnostic sequence and
decision-making order.

## 1. Trigger Conditions

A diagnostic sequence is triggered when any of the following occur on
a machine:

- Any sensor reading crosses from Normal into Warning or Critical
  (per that machine's Machine Manual thresholds).
- Any PLC alarm fires (see PLC Alarm Troubleshooting Guide).
- Reject rate exceeds the "investigation required" threshold in the
  Quality Troubleshooting SOP (generally >4%, machine-specific
  variants apply — see that document).
- Production rate drops more than 10 percentage points from the
  machine's rolling 7-day baseline.

## 2. Mandatory Diagnostic Sequence

The Agent MUST follow this order. Do not skip steps, and do not name a
root cause before completing them:

1. **Sensor validation** — call `get_machine_data()`. Confirm the
   reading is not a transient spike (compare to last 3 samples if
   available). Classify severity per the Machine Manual.
2. **PLC alarm check** — call `get_plc_alarms()`. Cross-reference
   active codes against the PLC Alarm Troubleshooting Guide. Note any
   documented alarm-pair correlations.
3. **Production and quality check** — call `get_production_quality()`.
   Compare reject rate and production rate against the Quality
   Troubleshooting SOP thresholds for this machine type.
4. **Maintenance history check** — call `get_maintenance_history()`
   filtered to this machine ID. Look for recurring problems, prior
   root causes, and whether a previous fix was temporary
   ("Temporary improvement" outcomes are a strong signal of an
   unresolved underlying issue).
5. **Knowledge base search** — call `search_maintenance_knowledge()`
   with the observed symptoms, alarm codes, and machine ID as the
   query. Retrieve the relevant SOP(s) (Bearing Failure SOP for
   rotating equipment, or the equivalent mechanism-specific document
   for that machine type).
6. **Synthesize evidence** — combine steps 1–5 into a single evidence
   set before reasoning about probable cause.

## 3. Generic Diagnostic Flow (Rotating Equipment: M-101, M-102, M-103)

```
High vibration
     ↓
Check temperature
     ↓
Check PLC alarms
     ↓
Check maintenance history
     ↓
Check lubrication
     ↓
Inspect bearing / joint mechanism
     ↓
Check alignment
```

## 4. Generic Diagnostic Flow (Process Equipment: M-104, M-105)

```
Reject rate rising / cycle instability
     ↓
Check process parameter (temperature / hydraulic pressure)
     ↓
Check PLC alarms
     ↓
Check maintenance history
     ↓
Check heater bands / seals / die alignment (per machine)
     ↓
Verify after adjustment
```

## 5. Confidence and Language Rules

- The Agent expresses probable cause with a confidence percentage,
  never as a certainty, unless a technician has physically confirmed
  it (see Bearing Failure SOP, Section "Confirmation Rule").
- If maintenance history shows two or more prior incidents with the
  same root cause on the same machine, confidence in that cause
  increases; state this reasoning explicitly in the evidence trail.
- If evidence sources conflict (e.g., PLC alarms suggest lubrication
  but history suggests bearing wear), the Agent must surface the
  conflict rather than silently picking one.

## 6. Corrective Action Principles

- Prefer the least disruptive action that is still safe: e.g.
  "reduce speed and inspect" before "full stop and replace part,"
  unless the Escalation Matrix or Safety Procedure mandates an
  immediate stop.
- Always include a verification step in the recommendation — a
  recommendation without a defined "how we'll know it worked" is
  incomplete.

## 7. Verification Procedure

After corrective action is taken, the Agent re-checks the same sensors
that triggered the incident, using the machine's Normal thresholds
from the Machine Manual. All relevant parameters must return to Normal
range, and reject/production rates must recover, before the incident
is marked RESOLVED. Partial recovery is marked MONITORING, not
RESOLVED.
