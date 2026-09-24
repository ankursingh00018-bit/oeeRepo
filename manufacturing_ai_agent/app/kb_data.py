"""
Static fleet knowledge extracted from the knowledge base documents.
This is the "structured" half of the knowledge base — thresholds and
alarm tables the Agent needs to evaluate numerically. The prose SOPs
in app/knowledge_base/*.md are retrieved separately via TF-IDF (see
rag.py) to support the Agent's reasoning/evidence text.
"""

# Per-machine sensor thresholds: (normal_max, warning_max) — anything
# above warning_max is CRITICAL. For sensors where LOW is bad (e.g.
# coolant flow), a "low_is_bad" threshold pair is given instead.
MACHINES = {
    "M-101": {
        "machine_type": "CNC Lathe",
        "thresholds": {
            "spindle_temperature_c": {"normal_max": 70, "warning_max": 82},
            "vibration_mm_s": {"normal_max": 3.0, "warning_max": 4.5, "escalate_above": 6.0},
            "spindle_load_pct": {"normal_max": 65, "warning_max": 80},
            "coolant_flow_lpm": {"low_is_bad": True, "warning_min": 5, "critical_min": 5},
        },
        "quality": {"normal_max": 2.0, "investigate_above": 4.0},
    },
    "M-102": {
        "machine_type": "CNC Milling Machine",
        "thresholds": {
            "temperature_c": {"normal_max": 75, "warning_max": 85},
            "vibration_mm_s": {"normal_max": 3.5, "warning_max": 5.0, "escalate_above": 7.0},
            "spindle_load_pct": {"normal_max": 70, "warning_max": 85},
            "coolant_temperature_c": {"normal_max": 30, "warning_max": 38},
        },
        "quality": {"normal_max": 2.0, "investigate_above": 4.0},
        "production": {"normal_min": 90, "warning_min": 80},
    },
    "M-103": {
        "machine_type": "Robotic Welding Cell",
        "thresholds": {
            "joint3_servo_temperature_c": {"normal_max": 65, "warning_max": 78},
            "joint_vibration_mm_s": {"normal_max": 2.5, "warning_max": 4.0},
            "wire_feed_tension_n": {"normal_min": 8, "normal_max": 14, "warning_max": 18},
            "shielding_gas_flow_lpm": {"low_is_bad": True, "warning_min": 9, "critical_min": 9},
        },
        "quality": {"normal_max": 1.5, "investigate_above": 3.5},
    },
    "M-104": {
        "machine_type": "Injection Molding Machine",
        "thresholds": {
            "barrel_zone2_temperature_c": {"normal_max": 230, "warning_max": 245},
            "hydraulic_pressure_bar": {"normal_max": 130, "warning_max": 150},
            "cycle_time_variance_pct": {"normal_max": 5, "warning_max": 12},
            "screw_vibration_mm_s": {"normal_max": 2.0, "warning_max": 3.2},
        },
        "quality": {"normal_max": 2.5, "investigate_above": 5.0},
    },
    "M-105": {
        "machine_type": "Hydraulic Stamping Press",
        "thresholds": {
            "hydraulic_oil_temperature_c": {"normal_max": 60, "warning_max": 72},
            "ram_vibration_mm_s": {"normal_max": 3.0, "warning_max": 4.8},
            "hydraulic_pressure_bar": {"normal_max": 220, "warning_max": 240},
            "die_alignment_deviation_mm": {"normal_max": 0.15, "warning_max": 0.30},
        },
        "quality": {"normal_max": 1.8, "investigate_above": 3.5},
    },
}

# PLC alarm code table (from Document 4)
PLC_ALARMS = {
    "ALM-118": {"meaning": "Spindle overload", "machines": ["M-101", "M-102"], "tier": "MEDIUM"},
    "ALM-221": {"meaning": "High spindle vibration", "machines": ["M-101", "M-102"], "tier": "HIGH"},
    "ALM-307": {"meaning": "High spindle temperature", "machines": ["M-101", "M-102"], "tier": "HIGH"},
    "ALM-412": {"meaning": "Low lubrication pressure", "machines": ["M-101", "M-102", "M-103"], "tier": "MEDIUM"},
    "ALM-501": {"meaning": "Emergency stop activated", "machines": ["ALL"], "tier": "CRITICAL"},
    "ALM-535": {"meaning": "Joint servo overtemperature", "machines": ["M-103"], "tier": "HIGH"},
    "ALM-548": {"meaning": "Wire feed tension fault", "machines": ["M-103"], "tier": "MEDIUM"},
    "ALM-612": {"meaning": "Barrel heater band fault", "machines": ["M-104"], "tier": "HIGH"},
    "ALM-624": {"meaning": "Hydraulic pressure out of range", "machines": ["M-104"], "tier": "MEDIUM"},
    "ALM-701": {"meaning": "Ram vibration high", "machines": ["M-105"], "tier": "HIGH"},
    "ALM-712": {"meaning": "Die alignment deviation", "machines": ["M-105"], "tier": "HIGH"},
    "ALM-724": {"meaning": "Hydraulic oil overtemperature", "machines": ["M-105"], "tier": "MEDIUM"},
}

# Documented alarm-pair correlations (from Document 4)
ALARM_CORRELATIONS = [
    {
        "codes": {"ALM-221", "ALM-307"},
        "note": "High-priority mechanical incident — strongly suggestive of spindle bearing "
                "degradation, but remains 'probable' until physically inspected.",
        "probable_cause": "Bearing degradation",
        "confidence_boost": 35,
    },
    {
        "codes": {"ALM-412"},
        "note": "Lubrication should be investigated and ruled out BEFORE declaring bearing "
                "failure — lubrication failure can mimic bearing wear.",
        "probable_cause": "Lubrication degraded",
        "confidence_boost": 20,
    },
    {
        "codes": {"ALM-612"},
        "note": "Typically indicates heater band failure producing short shots or flash, "
                "not a mechanical wear issue.",
        "probable_cause": "Heater band failure",
        "confidence_boost": 30,
    },
    {
        "codes": {"ALM-712"},
        "note": "Die alignment deviation combined with rising rejects requires an immediate "
                "stop — continuing risks die damage.",
        "probable_cause": "Die misalignment",
        "confidence_boost": 30,
    },
    {
        "codes": {"ALM-548"},
        "note": "Wire feed tension fault is a feed-mechanism issue, distinct from joint "
                "servo/bearing problems.",
        "probable_cause": "Wire feed mechanism wear",
        "confidence_boost": 25,
    },
]

BEARING_MACHINES = {"M-101", "M-102", "M-103"}
