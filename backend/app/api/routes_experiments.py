"""Experiment routes for listing and viewing experiments."""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..storage import repo
from ..storage.db import get_db
from ..storage.models import User
from .deps import get_current_user

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _parse_metrics(metrics: str | None) -> list[str]:
    if not metrics:
        return []
    try:
        payload = json.loads(metrics)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return []


class ExperimentPayload(BaseModel):
    id: str
    title: str
    objective: str
    hypothesis: str
    protocol: str
    duration_days: int
    start_date: str
    end_date: str
    status: str
    success_criteria: str
    metrics: list[str] = Field(default_factory=list)
    outcome: str | None = None


class ExperimentListResponse(BaseModel):
    experiments: List[ExperimentPayload]


@router.get("", response_model=ExperimentListResponse)
def list_experiments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    experiments = repo.list_experiments(db, user.id)
    payloads = [
        ExperimentPayload(
            id=experiment.id,
            title=experiment.title,
            objective=experiment.objective,
            hypothesis=experiment.hypothesis,
            protocol=experiment.protocol,
            duration_days=experiment.duration_days,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            status=experiment.status,
            success_criteria=experiment.success_criteria,
            metrics=_parse_metrics(experiment.metrics),
            outcome=experiment.outcome,
        )
        for experiment in experiments
    ]
    return ExperimentListResponse(experiments=payloads)


@router.get("/{experiment_id}", response_model=ExperimentPayload)
def get_experiment(
    experiment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    experiment = repo.get_experiment(db, user.id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return ExperimentPayload(
        id=experiment.id,
        title=experiment.title,
        objective=experiment.objective,
        hypothesis=experiment.hypothesis,
        protocol=experiment.protocol,
        duration_days=experiment.duration_days,
        start_date=experiment.start_date,
        end_date=experiment.end_date,
        status=experiment.status,
        success_criteria=experiment.success_criteria,
        metrics=_parse_metrics(experiment.metrics),
        outcome=experiment.outcome,
    )
