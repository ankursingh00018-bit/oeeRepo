# Document 3 — Bearing Failure SOP

Purpose: Specialized diagnostic knowledge for bearing-related failures
on rotating equipment. Applies primarily to M-101 (CNC Lathe spindle
bearing), M-102 (CNC Milling spindle bearing), and M-103 (robotic
joint servo bearings).

## 1. Symptoms

- Rising vibration trend over days-to-weeks, not just a single spike.
- Vibration and temperature rising together (bearing friction
  generates both).
- Audible high-frequency noise or "growling" during physical
  inspection (technician-reported, not sensor-derived).
- Reject rate creeping upward due to positional drift from bearing
  play.

## 2. Possible Causes (in order of frequency across the fleet)

1. **Bearing wear** — normal end-of-life degradation from accumulated
   duty cycles.
2. **Lubrication failure** — insufficient or degraded lubricant
   accelerates wear and raises both vibration and temperature. Check
   this BEFORE assuming wear (see PLC Alarm correlation with
   ALM-412).
3. **Misalignment** — shaft or joint misalignment causes uneven load
   and vibration that can mimic bearing wear.
4. **Mechanical overload** — sustained operation above rated spindle
   load or joint torque accelerates bearing fatigue.
5. **Contamination** — coolant, debris, or metal particulate ingress
   into the bearing housing.

## 3. Diagnostic Evidence to Collect

- Vibration trend over the last 30–90 days (not just current value).
- Whether a lubrication-related PLC alarm (ALM-412 family) is active
  or was recently cleared.
- Whether this exact machine has a prior bearing incident in
  maintenance history — recurrence strongly favors wear over a
  one-off cause.
- Spindle/joint load relative to rated capacity at time of incident.

## 4. Recommended Response (Escalating Order)

1. Reduce machine speed/load to reduce further degradation while
   investigation proceeds.
2. Initiate maintenance escalation per the Escalation Matrix.
3. Physically inspect bearing condition (noise, play, housing
   temperature by hand-check).
4. Check lubrication level, type, and delivery pressure.
5. Check mounting and housing integrity.
6. Check shaft/joint alignment if bearing and lubrication are ruled
   out.
7. Verify machine after any corrective action per the Maintenance SOP
   verification procedure.

## 5. Inspection Procedure Summary

Full checklist is in Document 8 (Maintenance Inspection Checklist).
Bearing-specific steps: controlled stop, lockout/tagout, listen for
bearing noise, check for radial/axial play by hand, inspect housing
for heat discoloration, check lubricant color and consistency.

## 6. Replacement Criteria

Replace the bearing if ANY of the following are confirmed during
physical inspection:

- Audible grinding, growling, or clicking under load.
- Measurable radial play beyond manufacturer spec for that bearing
  class.
- Visible pitting, discoloration from overheating, or contamination
  in the raceway.
- Lubricant shows metallic particulate.

If none of the above are confirmed but vibration remains elevated,
proceed to alignment check rather than replacing a bearing
speculatively.

## 7. Confirmation Rule — IMPORTANT

**Sensor data alone is NOT equivalent to a confirmed bearing failure.**
Vibration and temperature thresholds establish "probable cause" with a
stated confidence level. A physical inspection by a qualified
technician is always required before the Agent's final incident report
can state a confirmed root cause of "bearing failure" or "bearing
degradation confirmed." Until inspection occurs, the Agent's report
must use conditional language ("probable," "suspected") and must not
authorize part replacement on its own.

## 8. Verification After Bearing Replacement

Vibration and temperature must return to the Normal range defined in
that machine's Machine Manual entry, and reject rate must return below
the machine's normal threshold, sustained across at least one full
production cycle, before the incident is closed as RESOLVED.
