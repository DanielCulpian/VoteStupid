from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Option:
    text: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        """Valida que el texto de la opción no esté vacío."""
        if not self.text.strip():
            raise ValueError("El texto de la opción no puede estar vacío.")