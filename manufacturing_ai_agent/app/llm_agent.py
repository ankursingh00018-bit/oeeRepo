"""
LangChain-based reasoning core for the Manufacturing AI Agent.

This replaces the old rule-based / if-else decision tree
(_compute_severity, _reason_probable_cause, _build_recommendation) with
an actual LLM tool-calling agent (LangChain's `create_agent`). The agent
decides for itself:
  - which tools to call (machine data? alarms? history? KB search?),
  - in what order,
  - whether it needs more evidence before deciding,
  - and how to weigh conflicting signals,
instead of following a fixed sequence of Python branches. Its final
answer is still schema-validated (via `response_format=AgentAssessment`)
so the rest of the app can rely on it structurally -- only the reasoning
itself is delegated to the LLM, not the data contract.

Safety note -- read before changing this file:
The CRITICAL / emergency-stop short-circuit is deliberately NOT handled
here. It is checked in app/agent.py, deterministically, BEFORE this
module is ever invoked (Safety Procedure Section 4). That is intentional:
a hard safety interlock should never depend on an LLM's judgment or be
at the mercy of a prompt-injection-style failure mode. Everything this
module *is* responsible for -- severity for non-critical events, probable
cause, confidence, and recommended next steps -- is genuinely reasoned
by the LLM, not hardcoded.
"""
import json
import os
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field
from langchain.agents import create_agent

from . import tools as evidence_tools

# Names of the real evidence tools, used to filter the event log (the
# structured-output machinery can add its own internal tool call under
# the hood -- we only want to log the tools we actually defined).
_TOOL_NAMES = {
    "get_machine_data",
    "get_plc_alarms",
    "get_production_quality",
    "get_maintenance_history",
    "search_maintenance_knowledge",
}

# Human-readable labels for the live step stream (on_step callback below).
# Purely cosmetic -- the AgentEvent audit trail written to the DB still uses
# the exact technical "Agent called X(...) -> ..." message it always did.
_FRIENDLY_TOOL_LABEL = {
    "get_machine_data": "Reading live sensor data",
    "get_plc_alarms": "Checking PLC alarm codes",
    "get_production_quality": "Checking production quality / reject rate",
    "get_maintenance_history": "Reviewing maintenance history",
    "search_maintenance_knowledge": "Searching SOP knowledge base",
}


# --------------------------------------------------------------------------
# Structured output the agent must ultimately produce
# --------------------------------------------------------------------------

class AgentAssessment(BaseModel):
    """Final structured decision, schema-validated via LangChain's
    `response_format` so a malformed LLM answer is caught/retried rather
    than silently corrupting an Incident row."""

    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Incident severity for this NON-critical event. CRITICAL is "
                     "never assigned here -- E-stop / CRITICAL-alarm cases are "
                     "intercepted before this agent runs."
    )
    probable_cause: str = Field(
        description="Best-supported probable root cause, in a few words "
                     "(e.g. 'Bearing degradation', 'Heater band failure')."
    )
    confidence: int = Field(
        ge=0, le=100,
        description="Confidence in the probable cause, 0-100. Be conservative -- "
                     "if the evidence is thin or contradictory, say so and use a "
                     "lower number rather than inventing certainty.",
    )
    reasoning: str = Field(
        description="A few sentences a technician could audit: what evidence you "
                     "gathered and why it points to this severity/cause. Note "
                     "explicitly if the cause is only 'probable' pending physical "
                     "inspection."
    )
    recommendation: List[str] = Field(
        description="Ordered, concrete next steps for the technician on the floor."
    )


SYSTEM_PROMPT = """You are the reasoning core of a manufacturing floor AI agent. \
A machine has produced an abnormal sensor reading that has already been screened \
for safety-critical conditions (E-stop / CRITICAL alarms are handled elsewhere -- \
you will never be invoked for one of those).

Your job is to investigate like an experienced maintenance engineer would: gather \
evidence with your tools, weigh it, and produce a severity, probable cause, \
confidence level, and recommended next steps. Do not guess without checking -- use \
the tools.

Suggested investigation order (use judgment -- skip or repeat steps as the evidence \
warrants):
1. get_machine_data -- classify sensor readings against thresholds.
2. get_plc_alarms -- active alarms and any documented alarm-pair correlations.
3. get_production_quality -- reject rate / production rate impact.
4. get_maintenance_history -- has this machine had similar problems before? Two or \
   more prior incidents with a matching root cause should raise your confidence in \
   that cause.
5. search_maintenance_knowledge -- search the SOP / troubleshooting knowledge base \
   (use alarm codes, symptoms, or the machine type as your query) for anything that \
   confirms, rules out, or adds nuance to your working theory. Call it more than \
   once with different queries if your first search doesn't help.

Severity guidance (weigh the evidence like a human would -- these are not rigid \
thresholds):
- HIGH: multiple critical-tier sensor readings, a HIGH-tier alarm, or a severe \
  production-rate drop.
- MEDIUM: a single critical-tier sensor, a MEDIUM-tier alarm, or a reject rate that \
  crosses the machine's investigation threshold.
- LOW: warning-level signals only, or nothing beyond a watch-level reject rate.

A root cause is PROBABLE, never confirmed, until a technician physically inspects \
the machine -- say so in your reasoning when relevant (this matters especially for \
bearing-related causes, which lubrication problems can mimic).

Gather evidence first, then give your final severity, probable cause, confidence, \
reasoning, and recommendation."""


# --------------------------------------------------------------------------
# Tools -- thin wrappers around app/tools.py, bound to this investigation's
# reading via closures so the model only ever has to pass a machine_id.
# --------------------------------------------------------------------------

def _build_tools(reading: Dict[str, Any]) -> list:

    def get_machine_data(machine_id: str) -> dict:
        """Classify this machine's current sensor readings against its configured
        thresholds (NORMAL / WARNING / CRITICAL per sensor). Usually the right
        first call."""
        return evidence_tools.get_machine_data(machine_id, reading)

    def get_plc_alarms(machine_id: str) -> dict:
        """Get active PLC alarm codes for this reading, their meaning and tier,
        and any documented alarm-pair correlations to probable causes."""
        return evidence_tools.get_plc_alarms(reading)

    def get_production_quality(machine_id: str) -> dict:
        """Get reject rate / production rate and quality status
        (NORMAL / WATCH / INVESTIGATION_REQUIRED) for this machine."""
        return evidence_tools.get_production_quality(machine_id, reading)

    def get_maintenance_history(machine_id: str) -> list:
        """Get this machine's prior maintenance/incident history, most recent
        first -- use it to spot recurring root causes."""
        return evidence_tools.get_maintenance_history(machine_id)

    def search_maintenance_knowledge(query: str, top_k: int = 4) -> list:
        """Search the SOP / troubleshooting knowledge base (safety procedures,
        maintenance SOPs, alarm guides, checklists). Query with alarm codes,
        symptoms, or the machine type. Can be called more than once with
        different queries."""
        return evidence_tools.search_maintenance_knowledge(query, top_k=top_k)

    return [
        get_machine_data,
        get_plc_alarms,
        get_production_quality,
        get_maintenance_history,
        search_maintenance_knowledge,
    ]


# --------------------------------------------------------------------------
# LLM selection -- configurable via env vars so this isn't tied to one
# provider. Defaults to OpenAI; set LLM_PROVIDER=anthropic to use Claude.
# --------------------------------------------------------------------------


def _get_llm():

    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    model = os.getenv("LLM_MODEL")

    temperature = float(
        os.getenv("LLM_TEMPERATURE", "0")
    )

    # --------------------------------------------------
    # GEMINI
    # --------------------------------------------------

    if provider == "gemini":

        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.5-flash",
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    # --------------------------------------------------
    # ANTHROPIC
    # --------------------------------------------------

    elif provider == "anthropic":

        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model or "claude-sonnet-4-5",
            temperature=temperature
        )

    # --------------------------------------------------
    # OPENAI
    # --------------------------------------------------

    elif provider == "openai":

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            temperature=temperature
        )

    else:

        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider}. "
            f"Use gemini, openai, or anthropic."
        )



def _truncate(value: Any, limit: int = 400) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def run_agent_investigation(
    machine_id: str, reading: Dict[str, Any],
    on_step: Optional[Callable[[str, str], None]] = None,
) -> Tuple[AgentAssessment, List[Dict[str, str]], List[Dict[str, Any]]]:
    """
    Runs the LangChain agent over the evidence tools for one investigation.

    on_step, if given, is called synchronously as (event_type, message) the
    moment each tool call starts/finishes -- i.e. while the agent is still
    running, not after. app/agent.py passes a closure here that broadcasts
    each one over the WebSocket manager so every connected browser tab sees
    the investigation happen live instead of as one big blob at the end.
    It's purely a UX layer: if it's None, or if streaming isn't available
    for some reason, the investigation still runs and returns the exact
    same result via the agent.invoke() fallback below.

    Returns:
      - assessment: the agent's final, schema-validated AgentAssessment
      - event_log: [{"type": ..., "message": ...}, ...] -- one entry per
        tool call the agent made, suitable for writing straight to
        AgentEvent rows (this *is* the audit trail; the agent's own tool
        calls are the "steps" now, not fixed pipeline stages).
      - retrieved_documents: deduplicated KB chunks the agent actually
        pulled via search_maintenance_knowledge.
    """
    llm = _get_llm()
    tools = _build_tools(reading)

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        response_format=AgentAssessment,
    )

    user_input = (
        f"Investigate machine {machine_id}. Current reading:\n"
        f"{json.dumps(reading, indent=2)}"
    )

    seen_tool_starts: set = set()
    seen_tool_results: set = set()

    def _emit_live_steps(messages: List[Any]) -> None:
        """Diff-free by design: stream_mode='values' hands us the full
        accumulated message list on every step, so we track which tool
        calls/results we've already announced and only emit new ones."""
        if on_step is None:
            return
        for msg in messages:
            for tc in getattr(msg, "tool_calls", None) or []:
                tc_id = tc.get("id")
                if tc_id and tc_id not in seen_tool_starts:
                    seen_tool_starts.add(tc_id)
                    label = _FRIENDLY_TOOL_LABEL.get(tc["name"], tc["name"])
                    on_step("TOOL_START", f"{label}…")
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id and tool_call_id not in seen_tool_results:
                seen_tool_results.add(tool_call_id)
                name = getattr(msg, "name", None) or "tool"
                label = _FRIENDLY_TOOL_LABEL.get(name, name)
                on_step("TOOL_DONE", f"{label} — done")

    result = None
    try:
        # stream_mode="values" yields the full accumulated agent state
        # after every internal step, letting us announce each tool call
        # the moment it happens instead of only after agent.invoke()
        # returns everything at once.
        for step in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            stream_mode="values",
        ):
            result = step
            _emit_live_steps(step.get("messages", []) if isinstance(step, dict) else [])
    except Exception:
        # Streaming unavailable/failed for some reason (older langchain
        # version, unsupported stream_mode, etc.) -- fall back to the
        # plain blocking call so the investigation still completes
        # exactly as before, just without the live step-by-step updates.
        result = None

    if result is None:
        result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})

    # Map tool_call_id -> (name, args) from every AIMessage's tool calls,
    # then walk the ToolMessages (in execution order) to build the audit
    # log and pull out any KB documents that were retrieved.
    call_by_id: Dict[str, Dict[str, Any]] = {}
    for msg in result["messages"]:
        for tc in getattr(msg, "tool_calls", None) or []:
            call_by_id[tc["id"]] = {"name": tc["name"], "args": tc.get("args", {})}

    event_log: List[Dict[str, str]] = []
    retrieved_documents: List[Dict[str, Any]] = []

    for msg in result["messages"]:
        tool_call_id = getattr(msg, "tool_call_id", None)
        if tool_call_id is None:
            continue  # not a ToolMessage
        call = call_by_id.get(tool_call_id)
        name = call["name"] if call else getattr(msg, "name", "unknown_tool")
        if name not in _TOOL_NAMES:
            continue  # internal structured-output plumbing, not one of our tools

        args = call["args"] if call else {}
        try:
            parsed = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            parsed = msg.content

        event_log.append({
            "type": "TOOL_CALL",
            "message": f"Agent called {name}({args}) -> {_truncate(parsed)}",
        })

        if name == "search_maintenance_knowledge" and isinstance(parsed, list):
            for doc in parsed:
                if isinstance(doc, dict) and doc not in retrieved_documents:
                    retrieved_documents.append(doc)

    assessment = result.get("structured_response")
    if assessment is None:
        event_log.append({
            "type": "ERROR",
            "message": "Agent finished without producing a structured assessment -- "
                       "falling back to a conservative default so the incident isn't "
                       "left unassessed.",
        })
        assessment = AgentAssessment(
            severity="MEDIUM",
            probable_cause="Undetermined -- agent did not return a structured assessment",
            confidence=20,
            reasoning="The reasoning agent did not produce a final structured "
                      "assessment. Defaulting to MEDIUM and flagging for manual "
                      "review rather than under- or over-stating severity.",
            recommendation=["Manual technician review required -- automated "
                            "assessment did not complete."],
        )

    return assessment, event_log, retrieved_documents
