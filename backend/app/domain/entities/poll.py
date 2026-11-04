from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.option import Option
from app.domain.entities.poll_type import PollType


@dataclass
class Poll:
    title: str
    poll_type: PollType
    options: list[Option]

    description: str | None = None
    max_selections: int | None = None
    closes_at: datetime | None = None
    is_active: bool = True
    admin_token_hash: str | None = None

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self):
        """Valida el título, las opciones, el límite de selecciones y la zona horaria del cierre."""
        if not self.title.strip():
            raise ValueError("El título de la votación no puede estar vacío.")

        if len(self.options) < 2:
            raise ValueError("Una votación debe tener al menos dos opciones.")

        if self.poll_type != PollType.MULTIPLE_CHOICE:
            if self.max_selections is not None:
                raise ValueError(
                    "max_selections solo se puede utilizar en selección múltiple."
                )

        elif self.max_selections is not None:
            if not 1 <= self.max_selections <= len(self.options):
                raise ValueError(
                    "El máximo de selecciones debe estar entre 1 "
                    "y el número total de opciones."
                )

        if self.closes_at is not None:
            if self.closes_at.tzinfo is None:
                raise ValueError(
                    "La fecha de cierre debe incluir una zona horaria."
                )
