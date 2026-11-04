from collections.abc import Generator
from app.application.use_cases.cast_vote import CastVote
from app.application.use_cases.validate_vote_selection import ValidateVoteSelection
from sqlalchemy.orm import Session
from app.application.use_cases.update_vote import UpdateVote
from app.application.use_cases.get_poll_results import GetPollResults
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.repositories.sqlalchemy_poll_repository import (
    SqlAlchemyPollRepository,
)
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from app.infrastructure.security.admin_session import require_admin_session

from app.domain.entities.poll import Poll
from app.infrastructure.security.admin_token import verify_admin_token
from app.application.use_cases.close_poll import ClosePoll
from app.application.use_cases.reopen_poll import ReopenPoll

def get_db_session() -> Generator[Session, None, None]:
    """Proporciona una sesión de base de datos y la cierra al terminar la petición."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_poll_repository(
    db: Session = Depends(get_db_session),
) -> SqlAlchemyPollRepository:
    """Construye el repositorio SQLAlchemy con la sesión de la petición."""
    return SqlAlchemyPollRepository(db)

def get_cast_vote_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> CastVote:
    """Construye el caso de uso de registro de votos con su validador."""
    validate_vote_selection = ValidateVoteSelection(poll_repository)

    return CastVote(
        poll_repository=poll_repository,
        validate_vote_selection=validate_vote_selection,
    )

def get_update_vote_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> UpdateVote:
    """Construye el caso de uso de actualización de votos con su validador."""
    validate_vote_selection = ValidateVoteSelection(poll_repository)

    return UpdateVote(
        poll_repository=poll_repository,
        validate_vote_selection=validate_vote_selection,
    )

def get_poll_results_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> GetPollResults:
    """Construye el caso de uso de cálculo de resultados."""
    return GetPollResults(poll_repository)

def get_admin_poll(
    poll_id: UUID,
    x_admin_token: str | None = Header(None, alias="X-Admin-Token", min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$"),
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
    administrator = Depends(require_admin_session),
) -> Poll:
    """Obtiene la votación y comprueba el token privado de administración."""
    poll = poll_repository.get_by_id(poll_id)

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Votación no encontrada.",
        )

    if x_admin_token is not None and not verify_admin_token(x_admin_token, poll.admin_token_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de administrador inválido.",
        )

    return poll

def get_close_poll_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> ClosePoll:
    """Construye el caso de uso de cierre de votaciones."""
    return ClosePoll(poll_repository)


def get_reopen_poll_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> ReopenPoll:
    """Construye el caso de uso de reapertura de votaciones."""
    return ReopenPoll(poll_repository)
