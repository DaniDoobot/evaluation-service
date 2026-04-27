import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
from app.services.drive_service import upload_file_to_drive

router = APIRouter(prefix="/conversations", tags=["Conversations"])


ALLOWED_MIME_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
}


@router.post("/upload", response_model=ConversationOut)
async def upload_conversation_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not drive_folder_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_DRIVE_FOLDER_ID no está configurado",
        )

    filename = file.filename or "audio_sin_nombre"
    content_type = file.content_type or ""

    suffix = Path(filename).suffix.lower()

    valid_extension = suffix in [".mp3", ".wav"]
    valid_mime = content_type in ALLOWED_MIME_TYPES

    if not valid_extension and not valid_mime:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten ficheros mp3 o wav",
        )

    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="El fichero está vacío",
        )

    try:
        uploaded_file = upload_file_to_drive(
            file_content=file_content,
            filename=filename,
            mime_type=content_type or "application/octet-stream",
            folder_id=drive_folder_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo el fichero a Google Drive: {str(exc)}",
        )

    conversation = Conversation(
        original_filename=filename,
        file_mime_type=content_type,
        drive_file_id=uploaded_file.get("id"),
        drive_file_url=uploaded_file.get("webViewLink"),
        status="uploaded",
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


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