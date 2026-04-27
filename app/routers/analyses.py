from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Analysis, Conversation, EvaluationPrompt
from app.schemas import (
    AnalysisCreate,
    AnalysisComplete,
    AnalysisFail,
    AnalysisOut,
)
from app.services.drive_service import download_file_from_drive
from app.services.openai_analysis import (
    analyze_audio_with_openai_chat_completions,
    build_evaluation_prompt,
)

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.post("", response_model=AnalysisOut)
def create_analysis(
    payload: AnalysisCreate,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == payload.conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    prompt = (
        db.query(EvaluationPrompt)
        .filter(EvaluationPrompt.id == payload.prompt_id)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt no encontrado")

    analysis = Analysis(
        conversation_id=conversation.id,
        prompt_id=prompt.id,
        prompt_version=prompt.version,
        status="pending",
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


@router.get("", response_model=list[AnalysisOut])
def list_analyses(
    db: Session = Depends(get_db),
):
    return (
        db.query(Analysis)
        .order_by(Analysis.created_at.desc())
        .all()
    )


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id)
        .first()
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    return analysis


@router.post("/{analysis_id}/start", response_model=AnalysisOut)
def start_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id)
        .first()
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    analysis.status = "processing"
    analysis.started_at = datetime.utcnow()

    db.commit()
    db.refresh(analysis)

    return analysis


@router.post("/{analysis_id}/run", response_model=AnalysisOut)
def run_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id)
        .first()
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == analysis.conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    if not conversation.drive_file_id:
        raise HTTPException(
            status_code=400,
            detail="La conversación no tiene drive_file_id",
        )

    prompt = (
        db.query(EvaluationPrompt)
        .options(selectinload(EvaluationPrompt.criteria))
        .filter(EvaluationPrompt.id == analysis.prompt_id)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt no encontrado")

    analysis.status = "processing"
    analysis.started_at = datetime.utcnow()
    db.commit()

    try:
        audio_bytes = download_file_from_drive(conversation.drive_file_id)

        criteria = [
            {
                "code": c.code,
                "label": c.label,
                "description": c.description,
                "category": c.category,
                "scale_type": c.scale_type,
                "requires_feedback": c.requires_feedback,
                "weight": float(c.weight or 1),
                "is_active": c.is_active,
                "sort_order": c.sort_order,
            }
            for c in sorted(prompt.criteria, key=lambda item: item.sort_order)
            if c.is_active
        ]

        prompt_text = build_evaluation_prompt(
            base_instructions=prompt.base_instructions,
            criteria=criteria,
            output_schema=prompt.output_schema,
        )

        result_json = analyze_audio_with_openai_chat_completions(
            audio_bytes=audio_bytes,
            filename=conversation.original_filename,
            mime_type=conversation.file_mime_type or "audio/mpeg",
            prompt_text=prompt_text,
        )

        analysis.status = "completed"
        analysis.result_json = result_json
        analysis.error_message = None
        analysis.finished_at = datetime.utcnow()

        db.commit()
        db.refresh(analysis)

        return analysis

    except Exception as exc:
        analysis.status = "failed"
        analysis.error_message = str(exc)
        analysis.finished_at = datetime.utcnow()

        db.commit()
        db.refresh(analysis)

        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando análisis: {str(exc)}",
        )


@router.post("/{analysis_id}/complete", response_model=AnalysisOut)
def complete_analysis(
    analysis_id: int,
    payload: AnalysisComplete,
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id)
        .first()
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    analysis.status = "completed"
    analysis.result_json = payload.result_json
    analysis.finished_at = datetime.utcnow()
    analysis.error_message = None

    db.commit()
    db.refresh(analysis)

    return analysis


@router.post("/{analysis_id}/fail", response_model=AnalysisOut)
def fail_analysis(
    analysis_id: int,
    payload: AnalysisFail,
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id)
        .first()
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    analysis.status = "failed"
    analysis.error_message = payload.error_message
    analysis.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(analysis)

    return analysis