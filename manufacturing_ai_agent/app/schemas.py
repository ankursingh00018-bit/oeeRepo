from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class SimulateReading(BaseModel):
    reading: Dict[str, Any]


class InvestigateRequest(BaseModel):
    machine_id: str
    reading: Optional[Dict[str, Any]] = None  # if omitted, uses current live reading


class ApproveRequest(BaseModel):
    approved_by: str


class RejectRequest(BaseModel):
    rejected_by: str
    reason: Optional[str] = None


class VerifyRequest(BaseModel):
    reading: Dict[str, Any]
    final_root_cause: Optional[str] = None
    corrective_action: Optional[str] = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 3


class RecipientCreate(BaseModel):
    email: str
    name: Optional[str] = None
