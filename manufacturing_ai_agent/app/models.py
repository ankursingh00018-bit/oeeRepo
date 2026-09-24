from sqlalchemy import Column, String, Float, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


def now():
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True)
    machine_id = Column(String, index=True)
    machine_type = Column(String)
    severity = Column(String)
    status = Column(String, default="OPEN")  # OPEN, APPROVED, REJECTED, MONITORING, RESOLVED
    probable_cause = Column(String, nullable=True)
    confidence = Column(Integer, nullable=True)
    recommendation = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    observed_facts = Column(JSON, nullable=True)
    retrieved_documents = Column(JSON, nullable=True)

    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    verified_at = Column(DateTime, nullable=True)
    verification_result = Column(String, nullable=True)  # PASS / FAIL / PARTIAL
    post_action_readings = Column(JSON, nullable=True)
    final_root_cause = Column(String, nullable=True)
    corrective_action = Column(String, nullable=True)

    created_at = Column(DateTime, default=now)
    closed_at = Column(DateTime, nullable=True)

    events = relationship("AgentEvent", back_populates="incident", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="incident", cascade="all, delete-orphan")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"))
    machine_id = Column(String)
    priority = Column(String)
    title = Column(String)
    status = Column(String, default="OPEN")
    instructions = Column(JSON)
    created_at = Column(DateTime, default=now)

    incident = relationship("Incident", back_populates="work_orders")


class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=now)


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id"))
    event_type = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=now)

    incident = relationship("Incident", back_populates="events")
