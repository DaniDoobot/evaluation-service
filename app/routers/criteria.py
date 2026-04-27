from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EvaluationPrompt, EvaluationCriterion
from app.schemas import (
    EvaluationCriterionCreate,
    EvaluationCriterionUpdate,
    EvaluationCriterionOut,
)

router = APIRouter(tags=["Criteria"])


@router.post("/prompts/{prompt_id}/criteria", response_model=EvaluationCriterionOut)
def create_criterion(
    prompt_id: int,
    payload: EvaluationCriterionCreate,
    db: Session = Depends(get_db),
):
    prompt = (
        db.query(EvaluationPrompt)
        .filter(EvaluationPrompt.id == prompt_id)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt no encontrado")

    existing = (
        db.query(EvaluationCriterion)
        .filter(
            EvaluationCriterion.prompt_id == prompt_id,
            EvaluationCriterion.code == payload.code,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un criterio con ese code para este prompt",
        )

    criterion = EvaluationCriterion(
        prompt_id=prompt_id,
        code=payload.code,
        label=payload.label,
        description=payload.description,
        category=payload.category,
        scale_type=payload.scale_type,
        requires_feedback=payload.requires_feedback,
        weight=payload.weight,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )

    db.add(criterion)
    db.commit()
    db.refresh(criterion)

    return criterion


@router.put("/criteria/{criterion_id}", response_model=EvaluationCriterionOut)
def update_criterion(
    criterion_id: int,
    payload: EvaluationCriterionUpdate,
    db: Session = Depends(get_db),
):
    criterion = (
        db.query(EvaluationCriterion)
        .filter(EvaluationCriterion.id == criterion_id)
        .first()
    )

    if not criterion:
        raise HTTPException(status_code=404, detail="Criterio no encontrado")

    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(criterion, field, value)

    db.commit()
    db.refresh(criterion)

    return criterion


@router.delete("/criteria/{criterion_id}")
def delete_criterion(
    criterion_id: int,
    db: Session = Depends(get_db),
):
    criterion = (
        db.query(EvaluationCriterion)
        .filter(EvaluationCriterion.id == criterion_id)
        .first()
    )

    if not criterion:
        raise HTTPException(status_code=404, detail="Criterio no encontrado")

    db.delete(criterion)
    db.commit()

    return {
        "deleted": True,
        "criterion_id": criterion_id,
    }