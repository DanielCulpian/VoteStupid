from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

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