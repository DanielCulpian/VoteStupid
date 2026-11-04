from app.domain.entities.vote import Vote

from app.infrastructure.models.vote_model import VoteModel
from app.infrastructure.models.vote_selection_model import VoteSelectionModel


def to_model(vote: Vote) -> VoteModel:
    """Convierte el voto y sus selecciones a modelos SQLAlchemy."""
    selections = [
        VoteSelectionModel(
            option_id=option_id,
            position=position
        )
        for position, option_id in enumerate(vote.selected_option_ids)
    ]

    return VoteModel(
        id=vote.id,
        poll_id=vote.poll_id,
        voter_token_hash=vote.voter_token_hash,
        created_at=vote.created_at,
        updated_at=vote.updated_at,
        selections=selections
    )


def to_entity(vote_model: VoteModel) -> Vote:
    """Reconstruye el voto con sus selecciones ordenadas a partir de los modelos SQLAlchemy."""
    ordered_selections = sorted(
        vote_model.selections,
        key=lambda selection: (
            selection.position is None,
            selection.position if selection.position is not None else 0
        )
    )

    return Vote(
        id=vote_model.id,
        poll_id=vote_model.poll_id,
        voter_token_hash=vote_model.voter_token_hash,
        selected_option_ids=[
            selection.option_id
            for selection in ordered_selections
        ],
        created_at=vote_model.created_at,
        updated_at=vote_model.updated_at
    )