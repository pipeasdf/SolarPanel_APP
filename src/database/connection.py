"""
Database connection and session management for SQLite.

Provides engine creation, session factory, and database initialization.
"""

import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from .models import Base, Setting, DEFAULT_SETTINGS


# Database file path (in data directory)
def get_db_path() -> Path:
    """Get the path to the SQLite database file."""
    # Get the project root (parent of src)
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir / 'solar_data.db'


# Enable foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Global engine and session factory
_engine = None
_SessionFactory = None


def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine.
    
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    if _engine is None:
        db_path = get_db_path()
        db_url = f"sqlite:///{db_path}"
        _engine = create_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            connect_args={"check_same_thread": False}  # Allow multi-threaded access
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create the session factory.
    
    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    return _SessionFactory


def get_session() -> Session:
    """
    Create a new database session.
    
    Returns:
        New SQLAlchemy Session instance
    """
    SessionFactory = get_session_factory()
    return SessionFactory()


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Automatically handles commit/rollback and session closing.
    
    Usage:
        with get_session_context() as session:
            session.add(record)
            # Auto-commits on exit, rollback on exception
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(reset: bool = False) -> None:
    """
    Initialize the database.
    
    Creates all tables and inserts default settings if they don't exist.
    
    Args:
        reset: If True, drop all tables and recreate them
    """
    engine = get_engine()
    
    if reset:
        Base.metadata.drop_all(engine)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Insert default settings if not present
    with get_session_context() as session:
        for setting_data in DEFAULT_SETTINGS:
            existing = session.query(Setting).filter_by(key=setting_data['key']).first()
            if not existing:
                setting = Setting(**setting_data)
                session.add(setting)


def get_setting(key: str, default: str = None) -> str:
    """
    Get a setting value by key.
    
    Args:
        key: Setting key
        default: Default value if setting not found
        
    Returns:
        Setting value as string, or default if not found
    """
    with get_session_context() as session:
        setting = session.query(Setting).filter_by(key=key).first()
        return setting.value if setting else default


def set_setting(key: str, value: str, category: str = 'general', description: str = None) -> None:
    """
    Set a setting value.
    
    Creates the setting if it doesn't exist, updates if it does.
    
    Args:
        key: Setting key
        value: Setting value (will be converted to string)
        category: Setting category
        description: Optional description
    """
    with get_session_context() as session:
        setting = session.query(Setting).filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            if description:
                setting.description = description
        else:
            setting = Setting(
                key=key,
                value=str(value),
                category=category,
                description=description
            )
            session.add(setting)


def get_settings_by_category(category: str) -> dict:
    """
    Get all settings in a category as a dictionary.
    
    Args:
        category: Setting category
        
    Returns:
        Dictionary of key -> value
    """
    with get_session_context() as session:
        settings = session.query(Setting).filter_by(category=category).all()
        return {s.key: s.value for s in settings}
