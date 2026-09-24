# Document 6 — Escalation Matrix (Fleet-wide)

Purpose: Defines who is notified and what the Agent is authorized to
do at each severity level. Prevents the Agent from treating every
incident identically.

## Severity Table

| Severity | Condition | Notify | Agent Authorized Action |
|---|---|---|---|
| LOW | Any sensor in Warning band, no PLC alarm, reject rate in Watch band | Operator | Monitor; log trend; no recommendation issued yet |
| MEDIUM | Any sensor in Critical band, OR a MEDIUM-tier PLC alarm active, OR reject rate above Investigation threshold | Maintenance | Run full diagnostic sequence; recommend inspection |
| HIGH | Two or more Critical sensors, OR a HIGH-tier PLC alarm (e.g. ALM-221, ALM-307, ALM-535, ALM-701, ALM-712), OR production rate drop >15 points | Supervisor | Run full diagnostic sequence; generate recommendation; require human approval before any work order |
| CRITICAL | Emergency stop (ALM-501), safety interlock breach, or any condition in the Safety Procedure's prohibited-action list | Safety Team | Log and alert only — no diagnostic recommendation, no work order, no remote action |

## Notes

- Severity is determined by the WORST qualifying condition across all
  evidence sources (sensors, PLC alarms, quality data) — not an
  average.
- A machine can move DOWN in severity only after verification data
  confirms recovery per the Maintenance SOP verification procedure.
  The Agent may not downgrade severity based on a single improved
  reading alone.
- CRITICAL severity always overrides and short-circuits the normal
  Agent investigation flow — see Safety Procedure, Section 1.
- Repeated MEDIUM incidents on the same machine within 30 days should
  be flagged to the Supervisor even if no single incident reaches
  HIGH, since recurrence itself is a HIGH-relevant signal (see
  Maintenance SOP, Section 5).
