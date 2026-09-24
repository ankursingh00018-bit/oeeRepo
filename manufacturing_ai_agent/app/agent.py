"""
The Agent's orchestration layer. Implements the OBSERVE -> UNDERSTAND ->
INVESTIGATE -> REASON -> RECOMMEND flow from the project brief.

REASON/RECOMMEND are now delegated to a real LangChain tool-calling agent
(see app/llm_agent.py) that decides for itself which tools to call and how
to weigh the evidence, instead of a fixed if/else decision tree.

The one thing that stays deterministic, on purpose, is the CRITICAL /
emergency-stop short-circuit below: a hard safety gate should never depend
on an LLM's judgment, so it is checked in plain Python BEFORE the LLM
agent is ever invoked (Safety Procedure Section 4). Every AgentEvent
logged here -- deterministic or agent-driven -- is still a step a human
could audit.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from . import tools
from . import llm_agent
from .kb_data import MACHINES
from .models import Incident, AgentEvent, WorkOrder
from .ws_manager import manager

def _next_incident_id(db: Session) -> str:
    """
    Derive the next incident id from what's actually in the database,
    rather than an in-process counter. An in-memory itertools.count resets
    to its start value on every server restart (e.g. uvicorn --reload),
    while the SQLite file persists across restarts — causing a UNIQUE
    constraint collision the first time an old id is regenerated.
    """
    max_num = 1000
    for (existing_id,) in db.query(Incident.id).all():
        try:
            num = int(existing_id.split("-")[1])
        except (IndexError, ValueError):
            continue
        max_num = max(max_num, num)
    return f"INC-{max_num + 1}"


def _next_work_order_id(db: Session) -> str:
    """Same fix as _next_incident_id — derive from the DB, not an in-process counter."""
    max_num = 9999
    for (existing_id,) in db.query(WorkOrder.id).all():
        try:
            num = int(existing_id.split("-")[1])
        except (IndexError, ValueError):
            continue
        max_num = max(max_num, num)
    return f"WO-{max_num + 1}"


def _log(db: Session, incident_id: str, event_type: str, message: str):
    db.add(AgentEvent(incident_id=incident_id, event_type=event_type, message=message))


def _broadcast_investigation_result(incident: Incident) -> None:
    """Same payload shape as the /api/agent/investigate response -- every
    connected browser tab gets this the instant it's ready, instead of
    waiting on the poll in AgentContext.tsx to notice the finished row."""
    manager.broadcast_from_thread({
        "type": "investigation_result",
        "machine_id": incident.machine_id,
        "incident_id": incident.id,
        "severity": incident.severity,
        "confidence": incident.confidence,
        "probable_cause": incident.probable_cause,
        "recommendation": incident.recommendation,
        "retrieved_documents": incident.retrieved_documents,
        "evidence": incident.evidence,
        "status": incident.status,
    })


def investigate(db: Session, machine_id: str, reading: Dict[str, Any]) -> Incident:
    if machine_id not in MACHINES:
        raise ValueError(f"Unknown machine_id: {machine_id}")

    incident_id = _next_incident_id(db)
    machine_type = MACHINES[machine_id]["machine_type"]

    incident = Incident(
        id=incident_id,
        machine_id=machine_id,
        machine_type=machine_type,
        status="OPEN",
        observed_facts=reading,
    )
    db.add(incident)
    _log(db, incident_id, "INFO", "Agent started investigation")

    # Commit (and refresh) right away, before broadcasting anything. Without
    # this, the incident row only existed inside this function's still-open
    # transaction until the very end of investigate() -- invisible to any
    # OTHER request/connection, including the polling GET /api/incidents
    # call the frontend's cross-device sync loop makes every 6s. That poll
    # could land while this transaction was still open, see no incident for
    # this machine, and (wrongly) conclude the just-opened investigation had
    # already been cleared -- closing the chat drawer it had just opened via
    # the investigation_started broadcast below. Committing here first means
    # the incident is visible to every reader (WS-driven or polling) the
    # instant we say it's started.
    db.commit()
    db.refresh(incident)

    # Tell every connected browser tab an investigation has begun for this
    # machine -- this is what makes the chat window pop open live on every
    # other screen (see the WebSocket listener in AgentContext.tsx), not
    # just on whichever device clicked the abnormality button.
    manager.broadcast_from_thread({
        "type": "investigation_started",
        "machine_id": machine_id,
        "incident_id": incident_id,
    })

    # Deterministic safety gate — checked in plain Python BEFORE the LLM
    # agent is invoked, and never delegated to it. Per Safety Procedure
    # Section 4, a CRITICAL alarm (e.g. emergency stop) is logged and
    # escalated to the Safety Team with no probable-cause reasoning, no
    # recommendation, and no work order — full stop.
    alarm_data = tools.get_plc_alarms(reading)
    alarm_tiers = [a["tier"] for a in alarm_data["active_alarms"]]
    if "CRITICAL" in alarm_tiers:
        machine_data = tools.get_machine_data(machine_id, reading)
        incident.severity = "CRITICAL"
        incident.evidence = {"machine_data": machine_data, "alarms": alarm_data}
        incident.probable_cause = (
            "CRITICAL safety alarm detected (e.g. emergency stop). Handled under the "
            "Safety Procedure escalation path rather than root-cause reasoning."
        )
        incident.confidence = 100
        incident.recommendation = [
            "Do not restart the machine without Safety Team sign-off.",
            "Contact the Safety Team immediately and follow site Lockout/Tagout (LOTO) procedure.",
            "Preserve machine state and alarm logs for incident review.",
        ]
        _log(db, incident_id, "SAFETY", "CRITICAL alarm detected (e.g. emergency stop). "
             "Per Safety Procedure, this is flagged as a Safety Team escalation. "
             "Automated approval still proceeds per site configuration, but this "
             "incident requires Safety Team review independent of the work order.")
        db.commit()
        db.refresh(incident)
        _broadcast_investigation_result(incident)
        return incident

    _log(db, incident_id, "STEP", "No CRITICAL/E-stop alarm present — handing the "
         "investigation to the LangChain reasoning agent")

    def _on_step(event_type: str, message: str) -> None:
        # Fired live, from inside llm_agent's agent.stream() loop, as each
        # tool call starts/finishes -- broadcast immediately so connected
        # tabs see the investigation happen in real time instead of a
        # single blob once everything is done.
        manager.broadcast_from_thread({
            "type": "agent_step",
            "machine_id": machine_id,
            "incident_id": incident_id,
            "event_type": event_type,
            "message": message,
        })

    # The LLM agent takes it from here. It decides for itself which tools
    # to call, in what order, and synthesizes severity / probable cause /
    # confidence / recommendation — nothing below is a fixed if/else
    # decision tree. Every tool call it makes is logged as an AgentEvent
    # so the trace stays auditable.
    assessment, agent_events, retrieved_docs = llm_agent.run_agent_investigation(
        machine_id, reading, on_step=_on_step
    )
    for event in agent_events:
        _log(db, incident_id, event["type"], event["message"])

    # Evidence snapshot for the incident record / report. (The agent
    # fetched this same data itself via its tools to reason over it —
    # this call just captures a clean copy for storage/display.)
    machine_data = tools.get_machine_data(machine_id, reading)
    quality_data = tools.get_production_quality(machine_id, reading)
    history = tools.get_maintenance_history(machine_id)

    incident.severity = assessment.severity
    incident.probable_cause = assessment.probable_cause
    incident.confidence = assessment.confidence
    incident.recommendation = assessment.recommendation
    incident.retrieved_documents = retrieved_docs
    incident.evidence = {
        "machine_data": machine_data,
        "alarms": alarm_data,
        "quality": quality_data,
        "history_count": len(history),
    }
    incident.status = "OPEN"

    _log(db, incident_id, "REASONING", assessment.reasoning)

    if incident.severity in ("HIGH", "CRITICAL"):
        _log(db, incident_id, "SAFETY", "Human approval required before any work order is created "
             "(Safety Procedure, Section 2 / Section 5 architecture requirement).")

    db.commit()
    db.refresh(incident)
    _broadcast_investigation_result(incident)
    return incident


def approve_incident(db: Session, incident: Incident, approved_by: str) -> WorkOrder:
    incident.status = "APPROVED"
    incident.approved_by = approved_by
    incident.approved_at = datetime.now(timezone.utc)
    if incident.severity == "CRITICAL":
        _log(db, incident.id, "APPROVAL", f"CRITICAL incident approved by {approved_by} "
             "(Safety Team escalation still applies independently of this work order).")
    else:
        _log(db, incident.id, "APPROVAL", f"Action approved by {approved_by}")

    wo_id = _next_work_order_id(db)
    work_order = WorkOrder(
        id=wo_id,
        incident_id=incident.id,
        machine_id=incident.machine_id,
        priority=incident.severity,
        title=f"Investigate {incident.probable_cause} on {incident.machine_id}",
        status="OPEN",
        instructions=incident.recommendation,
    )
    db.add(work_order)
    _log(db, incident.id, "WORKFLOW", f"Work order {wo_id} created")
    db.commit()
    db.refresh(work_order)

    manager.broadcast_from_thread({
        "type": "incident_approved",
        "machine_id": incident.machine_id,
        "incident_id": incident.id,
        "status": incident.status,
        "approved_by": approved_by,
        "work_order": {
            "id": work_order.id,
            "incident_id": work_order.incident_id,
            "machine_id": work_order.machine_id,
            "priority": work_order.priority,
            "title": work_order.title,
            "status": work_order.status,
            "instructions": work_order.instructions,
            "created_at": work_order.created_at,
        },
    })

    return work_order


def reject_incident(db: Session, incident: Incident, rejected_by: str, reason: Optional[str]):
    incident.status = "REJECTED"
    msg = f"Action rejected by {rejected_by}"
    if reason:
        msg += f" — reason: {reason}"
    _log(db, incident.id, "APPROVAL", msg)
    db.commit()

    manager.broadcast_from_thread({
        "type": "incident_rejected",
        "machine_id": incident.machine_id,
        "incident_id": incident.id,
        "status": incident.status,
    })


def verify_recovery(db: Session, incident: Incident, reading: Dict[str, Any],
                     final_root_cause: Optional[str], corrective_action: Optional[str]) -> Incident:
    machine_data = tools.get_machine_data(incident.machine_id, reading)
    quality_data = tools.get_production_quality(incident.machine_id, reading)

    sensors_ok = machine_data["overall_severity_from_sensors"] == "NORMAL"
    quality_ok = quality_data["quality_status"] == "NORMAL"
    production_rate = reading.get("production_rate_pct")
    production_ok = production_rate is None or production_rate >= 90

    all_pass = sensors_ok and quality_ok and production_ok

    incident.post_action_readings = reading
    incident.verified_at = datetime.now(timezone.utc)
    incident.corrective_action = corrective_action

    if final_root_cause:
        incident.final_root_cause = final_root_cause
    elif all_pass:
        incident.final_root_cause = f"{incident.probable_cause} (confirmed by recovery verification)"

    if all_pass:
        incident.status = "RESOLVED"
        incident.verification_result = "PASS"
        incident.closed_at = datetime.now(timezone.utc)
        _log(db, incident.id, "VERIFICATION",
             "All recovery criteria passed (sensors, quality, production). Incident RESOLVED.")
    elif sensors_ok or quality_ok:
        incident.status = "MONITORING"
        incident.verification_result = "PARTIAL"
        _log(db, incident.id, "VERIFICATION",
             "Partial recovery — some but not all criteria passed. Status set to MONITORING.")
    else:
        incident.status = "OPEN"
        incident.verification_result = "FAIL"
        _log(db, incident.id, "VERIFICATION",
             "Recovery criteria failed. Incident remains OPEN for further action.")

    db.commit()
    db.refresh(incident)

    manager.broadcast_from_thread({
        "type": "incident_verified",
        "machine_id": incident.machine_id,
        "incident_id": incident.id,
        "status": incident.status,
        "verification_result": incident.verification_result,
    })

    return incident


def generate_incident_report(incident: Incident) -> str:
    ev = incident.evidence or {}
    alarms = ev.get("alarms", {}).get("active_alarms", [])
    alarm_codes = ", ".join(a["code"] for a in alarms) if alarms else "None"

    report = f"""
INCIDENT REPORT

Incident ID:            {incident.id}
Machine ID:              {incident.machine_id}
Machine Type:            {incident.machine_type}
Detection Time:          {incident.created_at}

--- Observed Parameters at Detection ---
{_format_dict(incident.observed_facts)}

--- PLC Alarms ---
Active Alarm Codes:      {alarm_codes}

--- Quality Impact ---
{_format_dict(ev.get("quality", {}))}

--- Historical Evidence ---
Prior Incidents on File: {ev.get("history_count", 0)}

--- Retrieved Knowledge Documents ---
{", ".join(sorted(set(d["source"] for d in (incident.retrieved_documents or [])))) or "None"}

--- Agent Assessment ---
Severity:                {incident.severity}
Probable Cause:          {incident.probable_cause}
Confidence:              {incident.confidence}%

--- Recommendation ---
{_format_list(incident.recommendation)}

--- Human Approval ---
Status:                  {incident.status}
Approved By:             {incident.approved_by or "-"}
Approval Time:           {incident.approved_at or "-"}

--- Verification Data ---
Post-Action Readings:    {_format_dict(incident.post_action_readings or {})}
Verification Result:     {incident.verification_result or "-"}

--- Final Root Cause ---
{incident.final_root_cause or "Not yet confirmed"}

--- Closure ---
Status:                  {incident.status}
Closure Time:            {incident.closed_at or "-"}
""".strip()
    return report


def _format_dict(d: dict) -> str:
    if not d:
        return "  (none)"
    return "\n".join(f"  {k}: {v}" for k, v in d.items())


def _format_list(lst) -> str:
    if not lst:
        return "  (none — CRITICAL incidents omit recommendations per Safety Procedure)"
    return "\n".join(f"  {i+1}. {s}" for i, s in enumerate(lst))
