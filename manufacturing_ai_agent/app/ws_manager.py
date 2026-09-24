"""
Lightweight WebSocket broadcast layer.

Nothing about the LangChain agent, its tools, prompts, or the DB models
changes because of this file. It exists purely so app/agent.py and
app/llm_agent.py can push "an investigation step just happened" events
out to every connected browser tab in real time, instead of tabs only
finding out via the periodic GET /api/incidents poll the frontend
already does (that poll is kept as a fallback for devices whose socket
drops -- see AgentContext.tsx on the frontend).

FastAPI's synchronous ("def", not "async def") path functions already
run inside Starlette's threadpool, and app/agent.py's investigate() /
approve_incident() / verify_recovery() are exactly that kind of function
-- so calls into this module happen from a worker thread, not the main
asyncio event loop. broadcast_from_thread() is the thread-safe entry
point for that; it hops back onto the loop via
asyncio.run_coroutine_threadsafe and is fire-and-forget by design (a
slow/gone client should never be able to stall an investigation).
"""
import asyncio
import json
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once from main.py's startup event, so broadcast_from_thread
        (invoked later from a worker thread) has a loop to schedule onto."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        if not self._connections:
            return
        payload = json.dumps(message, default=str)
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast_from_thread(self, message: Dict[str, Any]) -> None:
        """Thread-safe, fire-and-forget. Call this from anywhere (including
        the worker thread running the blocking LangChain agent) to push a
        JSON message to every connected browser tab."""
        if self._loop is None:
            # No event loop bound yet (e.g. broadcast attempted before
            # startup finished, or in a test harness) -- just skip it
            # rather than raising; live-streaming is a UX nicety, never
            # something the investigation's correctness depends on.
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)
        except RuntimeError:
            pass


# Single shared instance used across the whole app.
manager = ConnectionManager()
