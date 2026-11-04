
import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_database_url
from app.infrastructure.models.base import Base

# Importamos los modelos para registrar todas las tablas.
from app.infrastructure.models.poll_model import PollModel
from app.infrastructure.models.option_model import OptionModel
from app.infrastructure.models.vote_model import VoteModel
from app.infrastructure.models.vote_selection_model import VoteSelectionModel


@pytest.fixture(scope="session")
def test_engine():
    """Prepara el motor de votestupid_test y crea y elimina las tablas de la sesión de pruebas."""
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

    # Comprobamos la conexión antes de crear las tablas.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    # Creamos las tablas necesarias para los tests.
    Base.metadata.create_all(bind=engine)

    yield engine

    # Eliminamos las tablas al finalizar la sesión de tests.
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Proporciona una sesión de base de datos para la prueba y la cierra al finalizar."""
    session = Session(test_engine)

    try:
        yield session
    finally:
        session.close()
