from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    Numeric,
    ForeignKey,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class EvaluationPrompt(Base):
    __tablename__ = "evaluation_prompts"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    base_instructions = Column(Text, nullable=False)
    output_schema = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    criteria = relationship(
        "EvaluationCriterion",
        back_populates="prompt",
        cascade="all, delete-orphan",
    )

    analyses = relationship(
        "Analysis",
        back_populates="prompt",
    )


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"

    id = Column(BigInteger, primary_key=True, index=True)
    prompt_id = Column(
        BigInteger,
        ForeignKey("evaluation_prompts.id", ondelete="CASCADE"),
        nullable=False,
    )
    code = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    scale_type = Column(String(50), nullable=False, default="numeric_0_10")
    requires_feedback = Column(Boolean, nullable=False, default=True)
    weight = Column(Numeric(5, 2), default=1.00)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    prompt = relationship(
        "EvaluationPrompt",
        back_populates="criteria",
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    file_mime_type = Column(String(100))
    drive_file_id = Column(String(255))
    drive_file_url = Column(Text)
    duration_seconds = Column(Integer)
    status = Column(String(50), nullable=False, default="uploaded")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    transcriptions = relationship(
        "ConversationTranscription",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    analyses = relationship(
        "Analysis",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationTranscription(Base):
    __tablename__ = "conversation_transcriptions"

    id = Column(BigInteger, primary_key=True, index=True)
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    transcription_text = Column(Text, nullable=False)
    transcription_json = Column(JSONB)
    provider = Column(String(100))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    conversation = relationship(
        "Conversation",
        back_populates="transcriptions",
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(BigInteger, primary_key=True, index=True)
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    prompt_id = Column(
        BigInteger,
        ForeignKey("evaluation_prompts.id"),
        nullable=False,
    )
    prompt_version = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    result_json = Column(JSONB)
    error_message = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    conversation = relationship(
        "Conversation",
        back_populates="analyses",
    )

    prompt = relationship(
        "EvaluationPrompt",
        back_populates="analyses",
    )
