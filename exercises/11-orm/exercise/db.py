import os

from sqlalchemy import create_engine, event

def make_engine(echo=False):
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, echo=echo)

class QueryCounter:

    def __init__(self, engine):
        self.count = 0
        event.listen(engine, "before_cursor_execute", self._on_execute)

    def _on_execute(self, conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            self.count += 1
