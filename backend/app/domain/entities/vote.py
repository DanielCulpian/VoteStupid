from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class Vote:
    poll_id: UUID
    voter_token_hash: str
    selected_option_ids: list[UUID]

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self):
        """Valida el hash del participante y exige una selección no vacía y sin duplicados."""
        if not self.voter_token_hash.strip():
            raise ValueError("El identificador del votante no puede estar vacío.")

        if not self.selected_option_ids:
            raise ValueError("Un voto debe contener al menos una opción.")

        if len(self.selected_option_ids) != len(set(self.selected_option_ids)):
            raise ValueError("Un voto no puede contener opciones duplicadas.")

    def update_selection(self, selected_option_ids: list[UUID]) -> None:
        """Valida la nueva selección del voto y actualiza su fecha de modificación."""
        if not selected_option_ids:
            raise ValueError("Un voto debe contener al menos una opción.")

        if len(selected_option_ids) != len(set(selected_option_ids)):
            raise ValueError("Un voto no puede contener opciones duplicadas.")

        self.selected_option_ids = selected_option_ids
        self.updated_at = datetime.now(timezone.utc)