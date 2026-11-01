import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv

load_dotenv()

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "La variable de entorno DATABASE_URL no está configurada."
        )

    return database_url


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)