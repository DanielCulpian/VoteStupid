from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        """Initialize the WebSocket connection registry grouped by poll."""
        self.active_connections: dict[UUID, set[WebSocket]] = {}

    async def connect(self, poll_id: UUID, websocket: WebSocket):
        """Accept and register a WebSocket connection for a poll."""
        await websocket.accept()

        if poll_id not in self.active_connections:
            self.active_connections[poll_id] = set()

        self.active_connections[poll_id].add(websocket)

    def disconnect(self, poll_id: UUID, websocket: WebSocket):
        """Remove the connection and delete the poll group when it becomes empty."""
        connections = self.active_connections.get(poll_id)

        if connections is None:
            return

        connections.discard(websocket)

        if not connections:
            del self.active_connections[poll_id]

    async def broadcast(self, poll_id: UUID, message: dict):
        """Broadcast a message to a poll's clients and remove failed connections."""
        connections = self.active_connections.get(poll_id, set())

        disconnected = []

        for connection in list(connections):
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(poll_id, connection)


connection_manager = ConnectionManager()
