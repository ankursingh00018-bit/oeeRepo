import json
import os
from fastapi import APIRouter, HTTPException

from ..schemas import SimulateReading
from ..kb_data import MACHINES

router = APIRouter(prefix="/api/machines", tags=["machines"])

_LIVE_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "knowledge_base", "machines_live_data.json")

with open(_LIVE_DATA_FILE, "r", encoding="utf-8") as f:
    _seed = json.load(f)

# In-memory "current live reading" store, seeded from normal_baseline.
_live_state = {
    m["machine_id"]: dict(m["normal_baseline"]) for m in _seed["machines"]
}
_scenarios = {m["machine_id"]: m for m in _seed["machines"]}


@router.get("")
def list_machines():
    return [
        {"machine_id": mid, "machine_type": cfg["machine_type"]}
        for mid, cfg in MACHINES.items()
    ]


@router.get("/{machine_id}/live")
def get_live(machine_id: str):
    if machine_id not in _live_state:
        raise HTTPException(404, f"Unknown machine_id: {machine_id}")
    return {"machine_id": machine_id, **_live_state[machine_id]}


@router.post("/{machine_id}/simulate")
def simulate_reading(machine_id: str, body: SimulateReading):
    """Overwrite the in-memory live reading for a machine — used to
    simulate PLC/IIoT input for the demo (no real hardware required)."""
    if machine_id not in _live_state:
        raise HTTPException(404, f"Unknown machine_id: {machine_id}")
    _live_state[machine_id].update(body.reading)
    return {"machine_id": machine_id, **_live_state[machine_id]}


@router.post("/{machine_id}/simulate/abnormal")
def simulate_abnormal(machine_id: str):
    """Convenience endpoint: jump straight to this machine's seeded
    demo_abnormal_scenario from machines_live_data.json."""
    scenario = _scenarios.get(machine_id, {}).get("demo_abnormal_scenario")
    if not scenario:
        raise HTTPException(404, f"No demo_abnormal_scenario seeded for {machine_id}")
    _live_state[machine_id] = dict(scenario)
    return {"machine_id": machine_id, **_live_state[machine_id]}


@router.post("/{machine_id}/simulate/recovery")
def simulate_recovery(machine_id: str):
    """Convenience endpoint: jump to demo_recovery_scenario if seeded,
    otherwise fall back to the normal_baseline."""
    scenario = _scenarios.get(machine_id, {}).get("demo_recovery_scenario") or \
        _scenarios.get(machine_id, {}).get("normal_baseline")
    if not scenario:
        raise HTTPException(404, f"No recovery/baseline scenario seeded for {machine_id}")
    _live_state[machine_id] = dict(scenario)
    return {"machine_id": machine_id, **_live_state[machine_id]}


def get_current_reading(machine_id: str):
    """Used internally by the agent router when no reading is supplied."""
    return _live_state.get(machine_id)
