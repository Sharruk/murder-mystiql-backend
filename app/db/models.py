"""
SQLAlchemy ORM models for the MurderMystiQL 'game' schema.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    seat_no: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[Optional["Session"]] = relationship("Session", back_populates="participant", uselist=False)


class Level(Base):
    __tablename__ = "levels"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    order_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    story_context: Mapped[str] = mapped_column(Text, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    hint_text: Mapped[str] = mapped_column(Text, nullable=False)
    hint_penalty_seconds: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    unlocks_tables: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False)


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.participants.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    current_level_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("game.levels.id"), nullable=True
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    participant: Mapped["Participant"] = relationship("Participant", back_populates="session")
    current_level: Mapped[Optional["Level"]] = relationship("Level")
    level_progress: Mapped[List["LevelProgress"]] = relationship("LevelProgress", back_populates="session")
    submissions: Mapped[List["Submission"]] = relationship("Submission", back_populates="session")
    hints_used: Mapped[List["HintUsed"]] = relationship("HintUsed", back_populates="session")
    penalties: Mapped[List["Penalty"]] = relationship("Penalty", back_populates="session")
    proctor_violations: Mapped[List["ProctorViolation"]] = relationship("ProctorViolation", back_populates="session")


class LevelProgress(Base):
    __tablename__ = "level_progress"
    __table_args__ = {"schema": "game"}

    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.sessions.id", ondelete="CASCADE"), primary_key=True
    )
    level_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.levels.id", ondelete="CASCADE"), primary_key=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    solved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    session: Mapped["Session"] = relationship("Session", back_populates="level_progress")
    level: Mapped["Level"] = relationship("Level")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.levels.id", ondelete="CASCADE"), nullable=False
    )
    submitted_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["Session"] = relationship("Session", back_populates="submissions")
    level: Mapped["Level"] = relationship("Level")


class HintUsed(Base):
    __tablename__ = "hints_used"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.levels.id", ondelete="CASCADE"), nullable=False
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    penalty_applied_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped["Session"] = relationship("Session", back_populates="hints_used")
    level: Mapped["Level"] = relationship("Level")


class Penalty(Base):
    __tablename__ = "penalties"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["Session"] = relationship("Session", back_populates="penalties")


class ProctorViolation(Base):
    __tablename__ = "proctor_violations"
    __table_args__ = {"schema": "game"}

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("game.sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["Session"] = relationship("Session", back_populates="proctor_violations")
