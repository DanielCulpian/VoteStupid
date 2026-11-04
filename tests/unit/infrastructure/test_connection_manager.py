import asyncio
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect

from app.infrastructure.realtime.connection_manager import ConnectionManager


class Socket:
    def __init__(self, failure=None):
        """Prepara un transporte controlado que registra mensajes o simula una desconexión."""
        self.messages = []
        self.accepted = False
        self.failure = failure

    async def accept(self):
        """Registra la aceptación del transporte simulado."""
        self.accepted = True

    async def send_json(self, message):
        """Captura el mensaje enviado o produce el fallo preparado por la prueba."""
        if self.failure:
            raise self.failure
        self.messages.append(message)


@pytest.mark.parametrize("failure", [WebSocketDisconnect(), RuntimeError("closed"), OSError("broken pipe")])
def test_failed_subscriber_does_not_prevent_delivery_to_others(failure):
    """Retira clientes fallidos sin perder mensajes de los demás ni mezclar votaciones."""
    async def scenario():
        """Ejecuta conexiones, difusión y limpieza en un mismo bucle de eventos."""
        manager = ConnectionManager()
        poll_id, other_id = uuid4(), uuid4()
        healthy, failed, other = Socket(), Socket(failure), Socket()
        await manager.connect(poll_id, healthy)
        await manager.connect(poll_id, failed)
        await manager.connect(other_id, other)
        message = {"type": "results_updated", "results": {"total_votes": 2}}
        await manager.broadcast(poll_id, message)
        assert healthy.accepted and healthy.messages == [message]
        assert other.messages == []
        assert manager.active_connections[poll_id] == {healthy}
        manager.disconnect(poll_id, healthy)
        manager.disconnect(poll_id, healthy)
        assert poll_id not in manager.active_connections
        await manager.broadcast(poll_id, message)
        assert manager.active_connections[other_id] == {other}

    asyncio.run(scenario())
