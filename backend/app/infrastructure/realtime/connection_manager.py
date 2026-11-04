from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        """Inicializa el registro de conexiones WebSocket agrupadas por votación."""
        self.active_connections: dict[UUID, set[WebSocket]] = {}

    async def connect(self, poll_id: UUID, websocket: WebSocket):
        """Acepta y registra una conexión WebSocket asociada a una votación."""
        await websocket.accept()

        if poll_id not in self.active_connections:
            self.active_connections[poll_id] = set()

        self.active_connections[poll_id].add(websocket)

    def disconnect(self, poll_id: UUID, websocket: WebSocket):
        """Retira la conexión y elimina el grupo de la votación si queda vacío."""
        connections = self.active_connections.get(poll_id)

        if connections is None:
            return

        connections.discard(websocket)

        if not connections:
            del self.active_connections[poll_id]

    async def broadcast(self, poll_id: UUID, message: dict):
        """Envía un mensaje a los clientes de una votación y retira las conexiones fallidas."""
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
