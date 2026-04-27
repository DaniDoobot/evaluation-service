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
    AnalysisListItemOut,
    AnalysisDetailOut,
)
from app.services.drive_service import download_file_from_drive
from app.services.openai_analysis import (
    analyze_audio_with_openai_chat_completions,
    build_evaluation_prompt,
)

router = APIRouter(prefix="/analyses", tags=["Analyses"])


def _extract_global_score(result_json):
    if not isinstance(result_json, dict):
        return None

    criterios = result_json.get("criterios_generales")

    if isinstance(criterios, dict):
        evaluacion_global = criterios.get("evaluacion_global")

        if isinstance(evaluacion_global, dict):
            score = evaluacion_global.get("score")
            return float(score) if score is not None else None

        if isinstance(evaluacion_global, (int, float)):
            return float(evaluacion_global)

    direct_score = result_json.get("evaluacion_global")
    if isinstance(direct_score, (int, float)):
        return float(direct_score)

    return None


def _extract_tipo_conversacion(result_json):
    if not isinstance(result_json, dict):
        return None

    metadata = result_json.get("metadata")
    if isinstance(metadata, dict):
        tipo = metadata.get("tipo_conversacion")
        if tipo:
            return str(tipo)

    tipo_llamada = result_json.get("tipo_llamada")
    if tipo_llamada:
        return str(tipo_llamada)

    campos = result_json.get("campos_extraccion")
    if isinstance(campos, dict):
        resultado = campos.get("resultado")
        if resultado:
            return str(resultado)

    return None


def _analysis_to_list_item(analysis: Analysis) -> AnalysisListItemOut:
    return AnalysisListItemOut(
        id=analysis.id,
        status=analysis.status,
        conversation_id=analysis.conversation_id,
        conversation_filename=analysis.conversation.original_filename
        if analysis.conversation
        else None,
        conversation_drive_url=analysis.conversation.drive_file_url
        if analysis.conversation
        else None,
        prompt_id=analysis.prompt_id,
        prompt_name=analysis.prompt.name if analysis.prompt else None,
        prompt_version=analysis.prompt_version,
        evaluation_global_score=_extract_global_score(analysis.result_json),
        tipo_conversacion=_extract_tipo_conversacion(analysis.result_json),
        created_at=analysis.created_at,
        started_at=analysis.started_at,
        finished_at=analysis.finished_at,
    )


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


@router.get("/detail", response_model=list[AnalysisListItemOut])
def list_analyses_detail(
    db: Session = Depends(get_db),
):
    analyses = (
        db.query(Analysis)
        .options(
            selectinload(Analysis.conversation),
            selectinload(Analysis.prompt),
        )
        .order_by(Analysis.created_at.desc())
        .all()
    )

    return [_analysis_to_list_item(analysis) for analysis in analyses]


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


@router.get("/{analysis_id}/detail", response_model=AnalysisDetailOut)
def get_analysis_detail(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .options(
            selectinload(Analysis.conversation),
            selectinload(Analysis.prompt).selectinload(EvaluationPrompt.criteria),
        )
        .filter(Analysis.id == analysis_id)
        .first()
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    if analysis.prompt and analysis.prompt.criteria:
        analysis.prompt.criteria = sorted(
            analysis.prompt.criteria,
            key=lambda c: c.sort_order,
        )

    return AnalysisDetailOut(
        analysis=analysis,
        conversation=analysis.conversation,
        prompt=analysis.prompt,
    )


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