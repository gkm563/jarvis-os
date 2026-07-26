"""
Long-Term Relational Memory Module.
Manages persistent SQLite/PostgreSQL data storage for User Profiles, Contacts, Projects, and Task Logs.
"""

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from jarvis.config.settings import settings
from jarvis.core.models import UserProfile, AuditLogRecord
from jarvis.utils.logger import get_logger

logger = get_logger("LongTermMemory")

Base = declarative_base()


class DBUserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    default_browser = Column(String(32), default="chrome")
    locale = Column(String(32), default="en_US")
    preferences_json = Column(Text, default="{}")


class DBTaskExecutionLog(Base):
    __tablename__ = "task_execution_logs"

    task_id = Column(String(64), primary_key=True)
    user_goal = Column(Text, nullable=False)
    plan_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class LongTermMemory:
    """
    SQLAlchemy-backed long-term memory engine.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False} if "sqlite" in self.db_url else {})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info(f"Long-Term Memory initialized with database URL: {self.db_url}")

    def save_user_profile(self, profile: UserProfile) -> None:
        """Persists or updates a user profile."""
        session = self.SessionLocal()
        try:
            db_profile = session.query(DBUserProfile).filter_by(user_id=profile.user_id).first()
            if not db_profile:
                db_profile = DBUserProfile(user_id=profile.user_id)
                session.add(db_profile)

            db_profile.name = profile.name
            db_profile.default_browser = profile.default_browser
            db_profile.locale = profile.locale
            session.commit()
            logger.info(f"User profile saved for user_id: {profile.user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save user profile: {str(e)}")
        finally:
            session.close()

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieves a user profile by ID."""
        session = self.SessionLocal()
        try:
            db_profile = session.query(DBUserProfile).filter_by(user_id=user_id).first()
            if db_profile:
                return UserProfile(
                    user_id=db_profile.user_id,
                    name=db_profile.name,
                    default_browser=db_profile.default_browser,
                    locale=db_profile.locale,
                )
            return None
        finally:
            session.close()

    def log_task_execution(self, task_id: str, goal: str, plan_json: str, status: str, duration: float) -> None:
        """Records a task execution log for audit and reporting."""
        session = self.SessionLocal()
        try:
            db_log = DBTaskExecutionLog(
                task_id=task_id,
                user_goal=goal,
                plan_json=plan_json,
                status=status,
                duration_seconds=duration,
            )
            session.add(db_log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log task execution: {str(e)}")
        finally:
            session.close()
