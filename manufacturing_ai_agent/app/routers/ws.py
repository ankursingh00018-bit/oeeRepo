from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..ws_manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/agent")
async def agent_events_ws(websocket: WebSocket):
    """
    One of these is opened per browser tab (AgentContext.tsx on the
    frontend connects on mount, from every page). Purely a broadcast
    fan-out -- the client is never expected to send anything meaningful;
    we just keep reading so we notice a disconnect and can drop the
    socket from the connection set.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
