from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import InvestigateRequest
from .. import agent as agent_core
from . import machines as machines_router

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/investigate")
def investigate(body: InvestigateRequest, db: Session = Depends(get_db)):
    reading = body.reading or machines_router.get_current_reading(body.machine_id)
    if reading is None:
        raise HTTPException(404, f"No live reading available for {body.machine_id} "
                                  f"and none was supplied in the request.")
    try:
        incident = agent_core.investigate(db, body.machine_id, reading)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "incident_id": incident.id,
        "machine_id": incident.machine_id,
        "severity": incident.severity,
        "probable_cause": incident.probable_cause,
        "confidence": incident.confidence,
        "evidence": incident.evidence,
        "recommendation": incident.recommendation,
        "retrieved_documents": incident.retrieved_documents,
        "status": incident.status,
    }
