"""
WebSocket Real-Time Event & Telemetry Broadcaster for JARVIS OS.
Pushes step execution updates, security confirmations, and voice visualizer signals.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from jarvis.utils.logger import get_logger

logger = get_logger("WebSocketManager")
router = APIRouter(prefix="/v1", tags=["Realtime WebSocket"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WS message: {str(e)}")


ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received WS payload: {data}")
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
