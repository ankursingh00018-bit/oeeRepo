"""
Notification recipients. Replaces the old hard-coded single NOTIFY_TO_EMAIL
address -- recipients saved here (via the Recipients page) are who
/api/notify/email actually sends the work-order/incident emails to.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models
from ..schemas import RecipientCreate

router = APIRouter(prefix="/api/recipients", tags=["recipients"])


@router.get("")
def list_recipients(db: Session = Depends(get_db)):
    rows = db.query(models.Recipient).order_by(models.Recipient.created_at.asc()).all()
    return [
        {"id": r.id, "name": r.name, "email": r.email, "created_at": r.created_at}
        for r in rows
    ]


@router.post("")
def add_recipient(body: RecipientCreate, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Enter a valid email address.")

    recipient = models.Recipient(name=(body.name or "").strip() or None, email=email)
    db.add(recipient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"{email} is already in the recipient list.")
    db.refresh(recipient)
    return {"id": recipient.id, "name": recipient.name, "email": recipient.email, "created_at": recipient.created_at}


@router.delete("/{recipient_id}")
def delete_recipient(recipient_id: int, db: Session = Depends(get_db)):
    recipient = db.query(models.Recipient).filter(models.Recipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(404, "Recipient not found.")
    db.delete(recipient)
    db.commit()
    return {"deleted": True, "id": recipient_id}
