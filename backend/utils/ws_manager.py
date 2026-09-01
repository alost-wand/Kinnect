from fastapi import WebSocket
from collections import defaultdict
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, family_id: str):
        await websocket.accept()

        async with self.lock:
            self.active_connections[family_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, family_id: str):
        async with self.lock:
            if family_id in self.active_connections:
                if websocket in self.active_connections[family_id]:
                    self.active_connections[family_id].remove(websocket)

                if not self.active_connections[family_id]:
                    del self.active_connections[family_id]

    async def broadcast(self, family_id: str, message: dict):
        if family_id not in self.active_connections:
            return

        dead_connections = []

        # snapshot to avoid mutation issues
        connections = list(self.active_connections[family_id])

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # cleanup dead sockets
        if dead_connections:
            async with self.lock:
                for conn in dead_connections:
                    if conn in self.active_connections.get(family_id, []):
                        self.active_connections[family_id].remove(conn)

                if family_id in self.active_connections and not self.active_connections[family_id]:
                    del self.active_connections[family_id]

    async def broadcast_emergency(self, family_id: str, message: dict):
        message["channel"] = "emergency"
        message["priority"] = "high"
        await self.broadcast(family_id, message)


ws_manager = ConnectionManager()