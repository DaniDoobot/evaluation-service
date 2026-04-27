from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, ConversationTranscription
from app.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationOut,
    ConversationTranscriptionCreate,
    ConversationTranscriptionOut,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationOut)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
):
    conversation = Conversation(
        original_filename=payload.original_filename,
        file_mime_type=payload.file_mime_type,
        drive_file_id=payload.drive_file_id,
        drive_file_url=payload.drive_file_url,
        duration_seconds=payload.duration_seconds,
        status=payload.status,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
):
    return (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    return conversation


@router.put("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(conversation, field, value)

    db.commit()
    db.refresh(conversation)

    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    db.delete(conversation)
    db.commit()

    return {
        "deleted": True,
        "conversation_id": conversation_id,
    }


@router.post("/{conversation_id}/transcriptions", response_model=ConversationTranscriptionOut)
def create_transcription(
    conversation_id: int,
    payload: ConversationTranscriptionCreate,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    if payload.conversation_id != conversation_id:
        raise HTTPException(
            status_code=400,
            detail="El conversation_id del body no coincide con el de la URL",
        )

    transcription = ConversationTranscription(
        conversation_id=conversation_id,
        transcription_text=payload.transcription_text,
        transcription_json=payload.transcription_json,
        provider=payload.provider,
    )

    conversation.status = "transcribed"

    db.add(transcription)
    db.commit()
    db.refresh(transcription)

    return transcription


@router.get("/{conversation_id}/transcriptions", response_model=list[ConversationTranscriptionOut])
def list_transcriptions(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    return (
        db.query(ConversationTranscription)
        .filter(ConversationTranscription.conversation_id == conversation_id)
        .order_by(ConversationTranscription.created_at.desc())
        .all()
    )