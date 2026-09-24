import asyncio

from dotenv import load_dotenv

load_dotenv()  # picks up OPENAI_API_KEY / ANTHROPIC_API_KEY / LLM_PROVIDER / LLM_MODEL from .env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import machines, agent, incidents, work_orders, knowledge, notify, ws, recipients
from .ws_manager import manager

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Manufacturing AI Agent",
    description="Agentic system that investigates manufacturing abnormalities, "
                 "recommends corrective action, and verifies recovery after human approval.",
    version="1.0.0",
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://oee-online-nu.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(machines.router)
app.include_router(agent.router)
app.include_router(incidents.router)
app.include_router(work_orders.router)
app.include_router(knowledge.router)
app.include_router(notify.router)
app.include_router(recipients.router)
app.include_router(ws.router)


@app.on_event("startup")
async def _bind_ws_broadcast_loop():
    # investigate()/approve_incident()/verify_recovery() run inside
    # Starlette's threadpool (they're plain "def" endpoints), so the
    # broadcast manager needs a handle on the main event loop to safely
    # hop back onto it from that worker thread. See ws_manager.py.
    manager.bind_loop(asyncio.get_running_loop())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "message": "Manufacturing AI Agent API. See /docs for interactive Swagger UI.",
        "flow": "GET /api/machines -> POST /api/machines/{id}/simulate/abnormal -> "
                "POST /api/agent/investigate -> GET /api/incidents/{id} -> "
                "POST /api/incidents/{id}/approve -> POST /api/machines/{id}/simulate/recovery -> "
                "POST /api/incidents/{id}/verify -> GET /api/incidents/{id}/report",
    }
