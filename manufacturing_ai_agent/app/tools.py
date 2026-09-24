"""
The Agent's tools, matching the conceptual tool list in the project
brief: get_machine_data, get_plc_alarms, get_production_quality,
search_maintenance_knowledge, get_maintenance_history. (create_work_order,
notify_supervisor, generate_incident_report live in agent.py / routers
since they mutate state / format output rather than fetch evidence.)
"""
import csv
import os
from typing import Dict, Any, List

from .kb_data import MACHINES, PLC_ALARMS, ALARM_CORRELATIONS
from .rag import kb_index

HISTORY_CSV = os.path.join(os.path.dirname(__file__), "knowledge_base", "maintenance_history.csv")


def get_machine_data(machine_id: str, reading: Dict[str, Any]) -> Dict[str, Any]:
    """Classify each sensor in `reading` against this machine's thresholds."""
    config = MACHINES.get(machine_id)
    if not config:
        raise ValueError(f"Unknown machine_id: {machine_id}")

    classification = {}
    worst = "NORMAL"
    order = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}

    for sensor, value in reading.items():
        if sensor == "plc_alarms" or sensor not in config["thresholds"]:
            continue
        rule = config["thresholds"][sensor]
        status = _classify_sensor(value, rule)
        classification[sensor] = {"value": value, "status": status}
        if order[status] > order[worst]:
            worst = status

    return {
        "machine_id": machine_id,
        "machine_type": config["machine_type"],
        "reading": reading,
        "sensor_classification": classification,
        "overall_severity_from_sensors": worst,
    }


def _classify_sensor(value: float, rule: Dict[str, Any]) -> str:
    if rule.get("low_is_bad"):
        critical_min = rule.get("critical_min", rule.get("warning_min", 0))
        warning_min = rule.get("warning_min", critical_min)
        if value < critical_min:
            return "CRITICAL"
        if value < warning_min:
            return "WARNING"
        return "NORMAL"

    normal_max = rule.get("normal_max")
    warning_max = rule.get("warning_max", normal_max)
    if normal_max is not None and value <= normal_max:
        return "NORMAL"
    if warning_max is not None and value <= warning_max:
        return "WARNING"
    return "CRITICAL"


def get_plc_alarms(reading: Dict[str, Any]) -> Dict[str, Any]:
    codes = reading.get("plc_alarms", []) or []
    details = []
    for code in codes:
        info = PLC_ALARMS.get(code, {"meaning": "Unknown alarm code", "tier": "UNKNOWN"})
        details.append({"code": code, **info})

    correlations = []
    code_set = set(codes)
    for corr in ALARM_CORRELATIONS:
        if corr["codes"].issubset(code_set):
            correlations.append(
                {
                    "matched_codes": sorted(corr["codes"]),
                    "note": corr["note"],
                    "suggested_probable_cause": corr["probable_cause"],
                    "confidence_boost": corr["confidence_boost"],
                }
            )

    return {"active_alarms": details, "correlations": correlations}


def get_production_quality(machine_id: str, reading: Dict[str, Any]) -> Dict[str, Any]:
    config = MACHINES.get(machine_id, {})
    quality_cfg = config.get("quality", {"normal_max": 2.0, "investigate_above": 4.0})
    reject_rate = reading.get("reject_rate_pct")
    production_rate = reading.get("production_rate_pct")

    quality_status = "NORMAL"
    if reject_rate is not None:
        if reject_rate > quality_cfg["investigate_above"]:
            quality_status = "INVESTIGATION_REQUIRED"
        elif reject_rate > quality_cfg["normal_max"]:
            quality_status = "WATCH"

    return {
        "reject_rate_pct": reject_rate,
        "production_rate_pct": production_rate,
        "quality_status": quality_status,
        "normal_max_reject_pct": quality_cfg["normal_max"],
        "investigate_above_pct": quality_cfg["investigate_above"],
    }


def get_maintenance_history(machine_id: str) -> List[Dict[str, Any]]:
    if not os.path.exists(HISTORY_CSV):
        return []
    records = []
    with open(HISTORY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["machine_id"] == machine_id:
                records.append(row)
    # Most recent first
    records.sort(key=lambda r: r["date"], reverse=True)
    return records


def search_maintenance_knowledge(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    return kb_index.search(query, top_k=top_k)
