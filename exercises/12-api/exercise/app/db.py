import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def database_url():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

engine = create_engine(database_url(), echo=os.environ.get("SQL_ECHO", "1") == "1")
SessionLocal = sessionmaker(engine, expire_on_commit=False)
