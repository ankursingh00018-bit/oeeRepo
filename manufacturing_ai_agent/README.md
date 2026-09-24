# Manufacturing AI Agent

An agentic system that investigates manufacturing abnormalities,
reasons over factory knowledge + historical data, recommends
corrective action, waits for human approval before creating a work
order, and verifies recovery afterward:

```
OBSERVE -> UNDERSTAND -> INVESTIGATE -> REASON -> RECOMMEND ->
HUMAN APPROVAL -> TAKE ACTION -> VERIFY
```

Covers 5 fleet machines out of the box: **M-101** (CNC Lathe),
**M-102** (CNC Milling Machine — main demo unit), **M-103** (Robotic
Welding Cell), **M-104** (Injection Molding Machine), **M-105**
(Hydraulic Stamping Press).

Backend: FastAPI + SQLite (SQLAlchemy) + a local TF-IDF RAG index over
the 9 markdown knowledge-base documents in `app/knowledge_base/`, plus
a **LangChain tool-calling agent** (`app/llm_agent.py`) that does the
actual reasoning — it decides for itself which tools to call, in what
order, and how to weigh the evidence, rather than following a fixed
if/else decision tree. Requires an LLM API key (OpenAI or Anthropic —
see Setup below).

The one deliberate exception is the CRITICAL / emergency-stop
short-circuit in `agent.py`: that's a hard safety gate, checked in
plain Python *before* the LLM agent is ever invoked, per the Safety
Procedure. A safety interlock should never depend on an LLM's
judgment — everything else (severity, probable cause, confidence,
recommendation) is genuinely reasoned by the agent.

---

## 1. Setup

Requires Python 3.10+ and an API key for an LLM provider (OpenAI or
Anthropic).

```bash
cd manufacturing_ai_agent
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env: set LLM_PROVIDER (openai or anthropic) and the
# matching API key (OPENAI_API_KEY or ANTHROPIC_API_KEY)
```

By default the agent uses OpenAI's `gpt-4o-mini`. To use Claude
instead, set in `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## 2. Run

```bash
uvicorn app.main:app --reload
```

The API is now at `http://127.0.0.1:8000`.

Open `http://127.0.0.1:8000/docs` for the interactive Swagger UI —
you can run the entire demo below by clicking through it instead of
using curl, if you prefer.

A `manufacturing_agent.db` SQLite file is created automatically on
first run in the project folder. Delete it any time to reset all
incidents/work orders and start fresh.

---

## 3. Demo Walkthrough (M-102 bearing-degradation scenario)

All commands below use `curl`; every response is JSON.

**Step 1 — Check normal baseline**
```bash
curl http://127.0.0.1:8000/api/machines/M-102/live
```

**Step 2 — Inject the abnormal reading** (temperature 91°C, vibration
7.8 mm/s, ALM-221 + ALM-307, reject rate 6.4% — exactly the scenario
from the project brief):
```bash
curl -X POST http://127.0.0.1:8000/api/machines/M-102/simulate/abnormal
```
(Or push a custom reading: `POST /api/machines/M-102/simulate` with
body `{"reading": {"temperature_c": 91, ...}}`.)

**Step 3 — Run the Agent's investigation**
```bash
curl -X POST http://127.0.0.1:8000/api/agent/investigate \
  -H "Content-Type: application/json" \
  -d '{"machine_id": "M-102"}'
```
Returns `incident_id`, `severity` (HIGH), `probable_cause` ("Bearing
degradation"), `confidence` (~75%), the full evidence trail, retrieved
knowledge-base sections, and the recommended action list. Save the
`incident_id` from the response — you'll need it below.

**Step 4 — Inspect the full incident, including the Agent's step log**
```bash
curl http://127.0.0.1:8000/api/incidents/INC-1001
```
The `events` array shows exactly what the Agent did and in what order
(machine data retrieved → PLC alarms checked → quality checked →
history searched → knowledge base searched → root cause evaluated →
human approval flagged as required) — this is your audit trail.

**Step 5 — Human approval**
```bash
curl -X POST http://127.0.0.1:8000/api/incidents/INC-1001/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "Production Supervisor"}'
```
This creates a Work Order (`WO-....`) with inspection instructions
pulled from the recommendation.

**Step 6 — Simulate the technician fixing it and the machine recovering**
```bash
curl -X POST http://127.0.0.1:8000/api/machines/M-102/simulate/recovery
```

**Step 7 — Verify recovery**
```bash
curl -X POST http://127.0.0.1:8000/api/incidents/INC-1001/verify \
  -H "Content-Type: application/json" \
  -d '{"reading": {"temperature_c": 69, "vibration_mm_s": 2.2, "spindle_load_pct": 56, "coolant_temperature_c": 24, "reject_rate_pct": 1.1, "production_rate_pct": 97, "plc_alarms": []}, "corrective_action": "Bearing replaced"}'
```
Checks all recovery criteria (vibration/temperature back to Normal,
reject rate back to Normal, production rate ≥90%). If all pass, status
becomes `RESOLVED`.

**Step 8 — Get the final incident report**
```bash
curl http://127.0.0.1:8000/api/incidents/INC-1001/report
```
Plain-text report following the Incident Report Template.

---

## 4. Other Demo Scenarios (try the other 4 machines)

Every machine has a seeded abnormal scenario with a *different* root
cause, so you can show the Agent reasoning differently depending on
evidence — not just replaying the same bearing story:

| Machine | `POST /api/machines/{id}/simulate/abnormal` triggers... | Expected probable cause |
|---|---|---|
| M-101 | High vibration on the lathe spindle | Bearing degradation |
| M-102 | The brief's headline scenario | Bearing degradation |
| M-103 | Wire feed tension fault | Wire feed mechanism wear |
| M-104 | Barrel heater band fault + rising rejects | Heater band failure |
| M-105 | Ram vibration + die alignment deviation | Die misalignment |

Try, e.g.:
```bash
curl -X POST http://127.0.0.1:8000/api/machines/M-104/simulate/abnormal
curl -X POST http://127.0.0.1:8000/api/agent/investigate -H "Content-Type: application/json" -d '{"machine_id": "M-104"}'
```

**Safety/CRITICAL path** — push an emergency-stop alarm and see the
Agent refuse to reason or recommend, per the Safety Procedure:
```bash
curl -X POST http://127.0.0.1:8000/api/machines/M-105/simulate \
  -H "Content-Type: application/json" -d '{"reading": {"plc_alarms": ["ALM-501"]}}'
curl -X POST http://127.0.0.1:8000/api/agent/investigate -H "Content-Type: application/json" -d '{"machine_id": "M-105"}'
```
`severity` will be `CRITICAL` with an empty `recommendation` list —
the Agent logs and alerts only, exactly as the Safety Procedure
requires.

---

## 5. API Reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/api/machines` | List fleet machines |
| GET | `/api/machines/{id}/live` | Current simulated live reading |
| POST | `/api/machines/{id}/simulate` | Push a custom reading (partial update) |
| POST | `/api/machines/{id}/simulate/abnormal` | Jump to that machine's seeded fault scenario |
| POST | `/api/machines/{id}/simulate/recovery` | Jump to that machine's seeded recovery/baseline |
| POST | `/api/agent/investigate` | Run the Agent's full investigation |
| GET | `/api/incidents` | List all incidents |
| GET | `/api/incidents/{id}` | Incident detail + Agent event log + work orders |
| POST | `/api/incidents/{id}/approve` | Human approval → creates a Work Order |
| POST | `/api/incidents/{id}/reject` | Human rejection |
| POST | `/api/incidents/{id}/verify` | Submit post-fix readings, checks recovery criteria |
| GET | `/api/incidents/{id}/report` | Plain-text incident report |
| GET | `/api/work-orders` | List work orders |
| GET | `/api/work-orders/{id}` | Work order detail |
| GET | `/api/knowledge/documents` | List knowledge-base files |
| GET | `/api/knowledge/search?q=...&top_k=3` | Direct RAG search over the knowledge base |

---

## 6. Project Structure

```
manufacturing_ai_agent/
├── app/
│   ├── main.py                 FastAPI app, router registration
│   ├── database.py             SQLite/SQLAlchemy setup
│   ├── models.py                Incident, WorkOrder, AgentEvent tables
│   ├── schemas.py               Pydantic request bodies
│   ├── kb_data.py                Per-machine thresholds, PLC alarm table, correlations
│   ├── rag.py                    TF-IDF retrieval over app/knowledge_base/*.md
│   ├── tools.py                  Agent tools (get_machine_data, get_plc_alarms, etc.)
│   ├── llm_agent.py              LangChain tool-calling agent — the actual REASON/RECOMMEND step
│   ├── agent.py                  Orchestration: investigate(), approve(), verify(), report
│   ├── routers/
│   │   ├── machines.py           /api/machines
│   │   ├── agent.py               /api/agent
│   │   ├── incidents.py           /api/incidents
│   │   ├── work_orders.py         /api/work-orders
│   │   └── knowledge.py           /api/knowledge
│   └── knowledge_base/
│       ├── 01_machine_manual.md
│       ├── 02_maintenance_sop.md
│       ├── 03_bearing_failure_sop.md
│       ├── 04_plc_alarm_troubleshooting_guide.md
│       ├── 05_quality_troubleshooting_sop.md
│       ├── 06_escalation_matrix.md
│       ├── 07_safety_procedure.md
│       ├── 08_maintenance_inspection_checklist.md
│       ├── 09_incident_report_template.md
│       ├── maintenance_history.csv
│       └── machines_live_data.json
├── requirements.txt
├── .env.example
└── README.md
```

## 7. Design Notes / Where to Extend

- **Reasoning is a real LangChain agent, not a decision tree.**
  `app/llm_agent.py` builds a tool-calling agent
  (`create_tool_calling_agent` + `AgentExecutor`) over five tools —
  `get_machine_data`, `get_plc_alarms`, `get_production_quality`,
  `get_maintenance_history`, `search_maintenance_knowledge` — plus a
  terminal `submit_assessment` tool the agent calls with its final,
  structured (Pydantic-validated) severity / probable cause /
  confidence / recommendation. The agent chooses which tools to call,
  in what order, and whether to search the knowledge base more than
  once — nothing about that sequence is hardcoded. Every tool call it
  makes is written to the `AgentEvent` log (`TOOL_CALL` events) so the
  trace stays auditable even though the decisions aren't rule-based
  anymore.
- **The CRITICAL/E-stop safety gate stays deterministic on purpose.**
  It's checked in `agent.py` before `llm_agent.run_agent_investigation()`
  is ever called. Don't move this into the LLM agent's tools/prompt —
  a hard safety interlock shouldn't depend on model judgment or be
  exposed to prompt-injection-style failure modes.
- **Provider is swappable.** `LLM_PROVIDER=openai` (default,
  `gpt-4o-mini`) or `LLM_PROVIDER=anthropic` (`claude-sonnet-4-5`),
  set in `.env`. See `llm_agent._get_llm()`.
- **RAG is TF-IDF, not embeddings**, per the project brief's v1 plan.
  To upgrade: replace `app/rag.py`'s `KnowledgeBase` class internals
  with an embedding model + FAISS/Chroma/Qdrant; `tools.py` and
  `agent.py` call `search()` and don't need to change.
- **Severity vs. sensor-threshold "Critical" are different concepts.**
  A sensor crossing into its Critical band is strong *evidence*, but
  incident severity `CRITICAL` is reserved for actual safety events
  (E-stop / interlock breach) per the Escalation Matrix — don't
  conflate the two when extending the threshold logic in `kb_data.py`.
- **The `/simulate` endpoints exist because there's no real PLC** —
  swap `routers/machines.py`'s in-memory `_live_state` dict for a real
  MQTT/Modbus ingestion pipeline (see your PLC/IoT integration notes)
  when connecting to actual hardware; nothing else in the Agent needs
  to change since it only depends on the reading dict's shape.
