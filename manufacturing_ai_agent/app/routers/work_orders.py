from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WorkOrder

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.get("")
def list_work_orders(db: Session = Depends(get_db)):
    orders = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    return [
        {
            "id": w.id, "incident_id": w.incident_id, "machine_id": w.machine_id,
            "priority": w.priority, "title": w.title, "status": w.status,
            "instructions": w.instructions, "created_at": w.created_at,
        }
        for w in orders
    ]


@router.get("/{work_order_id}")
def get_work_order(work_order_id: str, db: Session = Depends(get_db)):
    w = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not w:
        raise HTTPException(404, f"Work order {work_order_id} not found")
    return {
        "id": w.id, "incident_id": w.incident_id, "machine_id": w.machine_id,
        "priority": w.priority, "title": w.title, "status": w.status,
        "instructions": w.instructions, "created_at": w.created_at,
    }
