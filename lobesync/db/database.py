from typing import Generator
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from lobesync.config import config
from .models import CheckList, Task, CheckListItem, Memory, Note, ChatSession, Message, ToolCall
import logging

logger = logging.getLogger(__name__)

engine = create_engine(config.DATABASE_URL)

def init_db():
    logger.info("Initializing database")
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e

def get_db() -> Generator[Session, None, None]:
    db: Session = Session(engine)
    try:
        yield db
    finally:
        db.close()
