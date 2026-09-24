from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import PlainTextResponse

from ..database import get_db
from ..models import Incident
from ..schemas import ApproveRequest, RejectRequest, VerifyRequest
from .. import agent as agent_core

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _get_or_404(db: Session, incident_id: str) -> Incident:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(404, f"Incident {incident_id} not found")
    return incident


def _serialize(incident: Incident):
    return {
        "id": incident.id,
        "machine_id": incident.machine_id,
        "machine_type": incident.machine_type,
        "severity": incident.severity,
        "status": incident.status,
        "probable_cause": incident.probable_cause,
        "confidence": incident.confidence,
        "recommendation": incident.recommendation,
        "evidence": incident.evidence,
        "observed_facts": incident.observed_facts,
        "retrieved_documents": incident.retrieved_documents,
        "approved_by": incident.approved_by,
        "approved_at": incident.approved_at,
        "verified_at": incident.verified_at,
        "verification_result": incident.verification_result,
        "final_root_cause": incident.final_root_cause,
        "corrective_action": incident.corrective_action,
        "created_at": incident.created_at,
        "closed_at": incident.closed_at,
        "events": [
            {"type": e.event_type, "message": e.message, "at": e.created_at}
            for e in sorted(incident.events, key=lambda e: e.id)
        ],
        "work_orders": [
            {"id": w.id, "priority": w.priority, "status": w.status, "title": w.title}
            for w in incident.work_orders
        ],
    }


@router.get("")
def list_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return [_serialize(i) for i in incidents]


@router.get("/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    return _serialize(_get_or_404(db, incident_id))


@router.post("/{incident_id}/approve")
def approve(incident_id: str, body: ApproveRequest, db: Session = Depends(get_db)):
    incident = _get_or_404(db, incident_id)
    if incident.status not in ("OPEN",):
        raise HTTPException(400, f"Incident is in status {incident.status}, cannot approve")
    try:
        work_order = agent_core.approve_incident(db, incident, body.approved_by)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"incident_id": incident.id, "status": incident.status,
            "work_order_id": work_order.id, "work_order_priority": work_order.priority}


@router.post("/{incident_id}/reject")
def reject(incident_id: str, body: RejectRequest, db: Session = Depends(get_db)):
    incident = _get_or_404(db, incident_id)
    agent_core.reject_incident(db, incident, body.rejected_by, body.reason)
    return {"incident_id": incident.id, "status": incident.status}


@router.post("/{incident_id}/verify")
def verify(incident_id: str, body: VerifyRequest, db: Session = Depends(get_db)):
    incident = _get_or_404(db, incident_id)
    updated = agent_core.verify_recovery(
        db, incident, body.reading, body.final_root_cause, body.corrective_action
    )
    return _serialize(updated)


@router.get("/{incident_id}/report", response_class=PlainTextResponse)
def report(incident_id: str, db: Session = Depends(get_db)):
    incident = _get_or_404(db, incident_id)
    return agent_core.generate_incident_report(incident)
