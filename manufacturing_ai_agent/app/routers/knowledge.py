import os
from fastapi import APIRouter

from ..rag import kb_index, KB_DIR

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/documents")
def list_documents():
    return sorted(f for f in os.listdir(KB_DIR) if f.endswith((".md", ".csv", ".json")))


@router.get("/search")
def search(q: str, top_k: int = 3):
    return kb_index.search(q, top_k=top_k)
