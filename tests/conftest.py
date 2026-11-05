
import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_database_url
from app.infrastructure.models.base import Base

# Import the models to register every table.
from app.infrastructure.models.poll_model import PollModel
from app.infrastructure.models.option_model import OptionModel
from app.infrastructure.models.vote_model import VoteModel
from app.infrastructure.models.vote_selection_model import VoteSelectionModel


@pytest.fixture(autouse=True)
def isolate_api_limits():
    """Isolate rate quotas between tests without disabling application protections."""
    from app.main import app
    from app.infrastructure.security.admin_session import require_admin_session
    # Earlier regression tests represent an authenticated organizer.
    # New authentication tests use instances without this override.
    app.dependency_overrides[require_admin_session] = lambda: None
    app.state.rate_limiter.clear()
    yield
    app.state.rate_limiter.clear()
    app.dependency_overrides.pop(require_admin_session, None)


@pytest.fixture(scope="session")
def test_engine():
    """Prepare the votestupid_test engine and create and drop the session's test tables."""
    database_url = make_url(get_database_url()).set(
        database="votestupid_test",
        host="127.0.0.1"
    )

    if database_url.database != "votestupid_test":
        raise RuntimeError(
            "Los tests solo pueden ejecutarse contra votestupid_test."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5}
    )

    # Check the connection before creating tables.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    # Create the tables required by the tests.
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop the tables when the test session finishes.
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Provide a database session for the test and close it afterwards."""
    session = Session(test_engine)

    try:
        yield session
    finally:
        session.close()
