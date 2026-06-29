"""Database connection and session management for PregAI"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings

engine = create_engine(settings.database_url)

if settings.database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_connection, _connection_record):
        previous_autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET search_path TO public")
        finally:
            cursor.close()
            dbapi_connection.autocommit = previous_autocommit

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
