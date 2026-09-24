# Document 4 — PLC Alarm Troubleshooting Guide (Fleet-wide)

Purpose: Maps PLC alarm codes to meaning, possible cause, recommended
response, and escalation requirement. Covers all five fleet machines.

## Alarm Code Table

| Code | Machine(s) | Meaning | Possible Cause | Recommended Response | Escalation |
|---|---|---|---|---|---|
| ALM-118 | M-101, M-102 | Spindle overload | Excessive cutting load, dull tool, feed rate too high | Reduce feed rate, check tool wear | MEDIUM |
| ALM-221 | M-101, M-102 | High spindle vibration | Bearing wear, misalignment, tool imbalance | Investigate per Bearing Failure SOP | HIGH |
| ALM-307 | M-101, M-102 | High spindle temperature | Bearing friction, coolant failure, overload | Check coolant flow first, then bearing | HIGH |
| ALM-412 | M-101, M-102, M-103 | Low lubrication pressure | Lubricant low, pump failure, blocked line | Investigate lubrication BEFORE declaring bearing failure | MEDIUM |
| ALM-501 | All | Emergency stop activated | Operator E-stop, safety interlock breach | Follow Safety Procedure — do not remotely reset | CRITICAL |
| ALM-535 | M-103 | Joint servo overtemperature | Servo overload, duty cycle exceeded, bearing wear in joint | Check duty cycle log, then joint bearing | HIGH |
| ALM-548 | M-103 | Wire feed tension fault | Feed roller wear, wire spool tangle, incorrect tension setting | Inspect feed mechanism — NOT a servo/bearing issue | MEDIUM |
| ALM-612 | M-104 | Barrel heater band fault | Heater element failure, thermocouple drift | Check heater band resistance, replace if open circuit | HIGH |
| ALM-624 | M-104 | Hydraulic pressure out of range | Pump wear, valve fault, oil viscosity issue | Check hydraulic pump and oil condition | MEDIUM |
| ALM-701 | M-105 | Ram vibration high | Die wear, misalignment, hydraulic pulsation | Investigate per Bearing/Alignment procedures | HIGH |
| ALM-712 | M-105 | Die alignment deviation | Die wear, mounting bolts loose, foundation shift | Stop and inspect die mounting immediately | HIGH |
| ALM-724 | M-105 | Hydraulic oil overtemperature | Cooler fault, oil degradation, pump inefficiency | Check hydraulic cooler and oil condition | MEDIUM |

## Documented Correlations (use these for reasoning, not single-alarm reads)

### ALM-221 + ALM-307 (M-101 / M-102)
Occurring together indicates a **high-priority mechanical incident** —
strongly suggestive of spindle bearing degradation, but per the Bearing
Failure SOP this remains "probable" until physically inspected.

### ALM-412 + High Vibration (any rotating machine)
Indicates lubrication should be investigated and ruled out BEFORE
declaring bearing failure. Lubrication failure can produce vibration
and temperature signatures that closely resemble bearing wear.

### ALM-535 + ALM-548 (M-103)
If both fire together, distinguish carefully: ALM-535 (servo/joint
bearing) and ALM-548 (wire feed mechanical) are different failure
families with different fixes. Do not treat a wire-feed fault as
evidence of a servo bearing problem or vice versa.

### ALM-612 + Rising Reject Rate (M-104)
Typically indicates heater band failure producing short shots or
flash, not a mechanical wear issue. See Quality Troubleshooting SOP.

### ALM-712 + Rising Reject Rate (M-105)
Die alignment deviation combined with rising rejects requires an
immediate stop — continuing risks die damage beyond the current batch
of rejected parts.

### ALM-501 (Emergency Stop) — any machine
Always CRITICAL. The Agent may only acknowledge and log this alarm. No
recommendation, work order, or remote action may be generated in place
of following the Safety Procedure.
