from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import EvaluationPrompt
from app.schemas import (
    EvaluationPromptCreate,
    EvaluationPromptUpdate,
    EvaluationPromptOut,
    EvaluationPromptDetailOut,
)

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.post("", response_model=EvaluationPromptOut)
def create_prompt(payload: EvaluationPromptCreate, db: Session = Depends(get_db)):
    if payload.is_active:
        db.query(EvaluationPrompt).update({"is_active": False})

    prompt = EvaluationPrompt(
        name=payload.name,
        description=payload.description,
        base_instructions=payload.base_instructions,
        output_schema=payload.output_schema,
        is_active=payload.is_active,
    )

    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return prompt


@router.get("", response_model=list[EvaluationPromptOut])
def list_prompts(db: Session = Depends(get_db)):
    return (
        db.query(EvaluationPrompt)
        .order_by(EvaluationPrompt.created_at.desc())
        .all()
    )


@router.get("/{prompt_id}", response_model=EvaluationPromptDetailOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = (
        db.query(EvaluationPrompt)
        .options(selectinload(EvaluationPrompt.criteria))
        .filter(EvaluationPrompt.id == prompt_id)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt no encontrado")

    prompt.criteria = sorted(prompt.criteria, key=lambda c: c.sort_order)

    return prompt


@router.put("/{prompt_id}", response_model=EvaluationPromptOut)
def update_prompt(
    prompt_id: int,
    payload: EvaluationPromptUpdate,
    db: Session = Depends(get_db),
):
    prompt = (
        db.query(EvaluationPrompt)
        .filter(EvaluationPrompt.id == prompt_id)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt no encontrado")

    data = payload.model_dump(exclude_unset=True)

    if data.get("is_active") is True:
        db.query(EvaluationPrompt).update({"is_active": False})

    for field, value in data.items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)

    return prompt


@router.post("/{prompt_id}/activate", response_model=EvaluationPromptOut)
def activate_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = (
        db.query(EvaluationPrompt)
        .filter(EvaluationPrompt.id == prompt_id)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt no encontrado")

    db.query(EvaluationPrompt).update({"is_active": False})
    prompt.is_active = True

    db.commit()
    db.refresh(prompt)

    return prompt