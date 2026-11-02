from collections.abc import Generator
from app.application.use_cases.cast_vote import CastVote
from app.application.use_cases.validate_vote_selection import ValidateVoteSelection
from fastapi import Depends
from sqlalchemy.orm import Session
from app.application.use_cases.update_vote import UpdateVote
from app.application.use_cases.get_poll_results import GetPollResults
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.repositories.sqlalchemy_poll_repository import (
    SqlAlchemyPollRepository,
)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_poll_repository(
    db: Session = Depends(get_db_session),
) -> SqlAlchemyPollRepository:
    return SqlAlchemyPollRepository(db)

def get_cast_vote_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> CastVote:
    validate_vote_selection = ValidateVoteSelection(poll_repository)

    return CastVote(
        poll_repository=poll_repository,
        validate_vote_selection=validate_vote_selection,
    )

def get_update_vote_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> UpdateVote:
    validate_vote_selection = ValidateVoteSelection(poll_repository)

    return UpdateVote(
        poll_repository=poll_repository,
        validate_vote_selection=validate_vote_selection,
    )

def get_poll_results_use_case(
    poll_repository: SqlAlchemyPollRepository = Depends(get_poll_repository),
) -> GetPollResults:
    return GetPollResults(poll_repository)