from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Analysis, Conversation, EvaluationPrompt
from app.schemas import (
    AnalysisCreate,
    AnalysisComplete,
    AnalysisFail,
    AnalysisOut,
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