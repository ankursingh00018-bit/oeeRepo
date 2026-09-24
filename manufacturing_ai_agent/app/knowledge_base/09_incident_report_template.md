# Document 9 — Incident Report Template

Purpose: Defines the structure the Agent uses to auto-generate the
final incident report once an incident reaches RESOLVED or CLOSED
status.

```
INCIDENT REPORT

Incident ID:            <e.g. INC-1071>
Machine ID:              <e.g. M-102>
Machine Type:            <e.g. CNC Milling Machine>
Detection Time:          <timestamp>

--- Observed Parameters at Detection ---
Temperature:             <value + unit>
Vibration:               <value + unit>
Spindle Load / Pressure: <value + unit>
Production Rate:         <value %>
Reject Rate:             <value %>

--- PLC Alarms ---
Active Alarm Codes:      <list>
Alarm Correlation Notes: <e.g. "ALM-221 + ALM-307 = high-priority mechanical incident">

--- Production Impact ---
Production Rate Change:  <baseline -> observed>
Estimated Units Affected: <if available>

--- Quality Impact ---
Reject Rate Change:      <baseline -> observed>
Defect Type(s):          <e.g. dimensional variation, porosity, flash>

--- Historical Evidence ---
Prior Incidents (same machine): <list with dates and root causes>
Recurrence Assessment:   <e.g. "2nd bearing-related incident in 4 months">

--- Retrieved Knowledge Documents ---
Documents Consulted:     <list, e.g. Bearing Failure SOP, PLC Alarm Guide>

--- Agent Assessment ---
Severity:                <LOW / MEDIUM / HIGH / CRITICAL>
Probable Cause:          <stated with appropriate confidence language>
Confidence:              <percentage>
Evidence Summary:        <2-4 sentence synthesis>

--- Recommendation ---
Recommended Action:      <ordered list>

--- Human Approval ---
Approved By:             <name/role>
Approval Time:           <timestamp>
Approval Decision:       <APPROVED / REJECTED>

--- Work Order ---
Work Order ID:           <e.g. WO-10021>
Priority:                <LOW / MEDIUM / HIGH / CRITICAL>
Instructions:            <from Maintenance Inspection Checklist>

--- Corrective Action Taken ---
Action Performed:        <technician-reported>
Technician:              <name/ID>

--- Verification Data ---
Post-Action Readings:    <temperature, vibration, reject rate, production rate>
Verification Result:     <PASS / FAIL / PARTIAL>

--- Final Root Cause ---
Confirmed Root Cause:    <only after physical inspection per Bearing Failure SOP Section 7>

--- Closure ---
Status:                  <RESOLVED / MONITORING / CLOSED>
Closure Time:            <timestamp>
```

## Notes on Completing This Template

- Every section must be populated from actual tool-call evidence — the
  Agent must not fabricate values for sections it did not investigate.
- "Final Root Cause" may only be marked "confirmed" if a technician
  physically verified it (per Bearing Failure SOP, Section 7, and the
  equivalent confirmation requirement for process equipment). Prior to
  that, use "probable cause" language throughout the report, including
  in the Agent Assessment section.
- If the incident was CRITICAL (E-stop/safety), the Recommendation and
  Work Order sections are omitted entirely per the Safety Procedure.
