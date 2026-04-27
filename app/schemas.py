from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Evaluation Criteria
# -----------------------------------------------------------------------------


class EvaluationCriterionCreate(BaseModel):
    code: str
    label: str
    description: str
    category: str
    scale_type: str = "numeric_0_10"
    requires_feedback: bool = True
    weight: float = 1.0
    is_active: bool = True
    sort_order: int = 0


class EvaluationCriterionUpdate(BaseModel):
    code: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    scale_type: Optional[str] = None
    requires_feedback: Optional[bool] = None
    weight: Optional[float] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class EvaluationCriterionOut(BaseModel):
    id: int
    prompt_id: int
    code: str
    label: str
    description: str
    category: str
    scale_type: str
    requires_feedback: bool
    weight: Optional[float] = None
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# Evaluation Prompts
# -----------------------------------------------------------------------------


class EvaluationPromptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    base_instructions: str
    output_schema: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class EvaluationPromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_instructions: Optional[str] = None
    output_schema: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class EvaluationPromptOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    version: int
    is_active: bool
    is_archived: bool = False
    base_instructions: str
    output_schema: dict[str, Any]

    class Config:
        from_attributes = True


class EvaluationPromptDetailOut(EvaluationPromptOut):
    criteria: list[EvaluationCriterionOut] = []


class PromptDuplicateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    activate: bool = False


# -----------------------------------------------------------------------------
# Conversations
# -----------------------------------------------------------------------------


class ConversationCreate(BaseModel):
    original_filename: str
    file_mime_type: Optional[str] = None
    drive_file_id: Optional[str] = None
    drive_file_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: str = "uploaded"


class ConversationUpdate(BaseModel):
    original_filename: Optional[str] = None
    file_mime_type: Optional[str] = None
    drive_file_id: Optional[str] = None
    drive_file_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: Optional[str] = None


class ConversationOut(BaseModel):
    id: int
    original_filename: str
    file_mime_type: Optional[str] = None
    drive_file_id: Optional[str] = None
    drive_file_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# Conversation Transcriptions
# -----------------------------------------------------------------------------


class ConversationTranscriptionCreate(BaseModel):
    conversation_id: int
    transcription_text: str
    transcription_json: Optional[dict[str, Any]] = None
    provider: Optional[str] = None


class ConversationTranscriptionOut(BaseModel):
    id: int
    conversation_id: int
    transcription_text: str
    transcription_json: Optional[dict[str, Any]] = None
    provider: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# Analyses
# -----------------------------------------------------------------------------


class AnalysisCreate(BaseModel):
    conversation_id: int
    prompt_id: int


class AnalysisComplete(BaseModel):
    result_json: dict[str, Any]


class AnalysisFail(BaseModel):
    error_message: str


class AnalysisOut(BaseModel):
    id: int
    conversation_id: int
    prompt_id: int
    prompt_version: int
    status: str
    result_json: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisListItemOut(BaseModel):
    id: int
    status: str
    conversation_id: int
    conversation_filename: Optional[str] = None
    conversation_drive_url: Optional[str] = None
    prompt_id: int
    prompt_name: Optional[str] = None
    prompt_version: int
    evaluation_global_score: Optional[float] = None
    tipo_conversacion: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class AnalysisDetailOut(BaseModel):
    analysis: AnalysisOut
    conversation: Optional[ConversationOut] = None
    prompt: Optional[EvaluationPromptDetailOut] = None
