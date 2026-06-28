"""Database connection and session management for PregAI"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()