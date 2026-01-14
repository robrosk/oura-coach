"""Experiment agent built on top of the Oura agent."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from langchain.tools import tool

from ..storage import repo
from ..storage.models import Experiment
from .oura_agent import OuraAgent, SYSTEM_PROMPT


@dataclass
class ExperimentSnapshot:
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
    metrics: list[str]
    outcome: str | None


def _parse_metrics(metrics: str | None) -> list[str]:
    if not metrics:
        return []
    try:
        parsed = json.loads(metrics)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _snapshot_experiment(experiment: Experiment) -> ExperimentSnapshot:
    return ExperimentSnapshot(
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


def _format_experiment_prompt(experiment: ExperimentSnapshot) -> str:
    payload = json.dumps(asdict(experiment), ensure_ascii=True, indent=2)
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "You are coaching the user through the experiment below. "
        "Use the experiment tools to update status or outcomes when appropriate.\n"
        f"Experiment details (JSON):\n{payload}"
    )


def _make_experiment_tools(db, user_id: str, experiment_id: str):
    @tool
    def end_experiment(summary: str | None = None) -> str:
        """Mark the experiment as ended."""
        experiment = repo.update_experiment_status(
            db,
            user_id,
            experiment_id,
            status="ended",
            outcome=summary,
        )
        if not experiment:
            return json.dumps({"error": "Experiment not found."})
        snapshot = _snapshot_experiment(experiment)
        return json.dumps({"status": snapshot.status, "experiment_id": snapshot.id})

    @tool
    def experiment_success(summary: str) -> str:
        """Mark the experiment as a success with a short outcome summary."""
        experiment = repo.update_experiment_status(
            db,
            user_id,
            experiment_id,
            status="success",
            outcome=summary,
        )
        if not experiment:
            return json.dumps({"error": "Experiment not found."})
        snapshot = _snapshot_experiment(experiment)
        return json.dumps({"status": snapshot.status, "experiment_id": snapshot.id})

    @tool
    def experiment_failure(summary: str) -> str:
        """Mark the experiment as a failure with a short outcome summary."""
        experiment = repo.update_experiment_status(
            db,
            user_id,
            experiment_id,
            status="failure",
            outcome=summary,
        )
        if not experiment:
            return json.dumps({"error": "Experiment not found."})
        snapshot = _snapshot_experiment(experiment)
        return json.dumps({"status": snapshot.status, "experiment_id": snapshot.id})

    return [end_experiment, experiment_success, experiment_failure]


class ExperimentAgent(OuraAgent):
    """Agent specialized for ongoing experiments.

    Inherits all Oura tools and adds experiment-specific actions.
    """

    name = "experiment_agent"

    def __init__(
        self,
        db,
        user_id: str,
        experiment_id: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
    ):
        experiment = repo.get_experiment(db, user_id, experiment_id)
        if not experiment:
            raise RuntimeError("Experiment not found")

        snapshot = _snapshot_experiment(experiment)
        prompt = _format_experiment_prompt(snapshot)
        tools = _make_experiment_tools(db, user_id, experiment_id)

        super().__init__(
            db=db,
            user_id=user_id,
            model=model,
            temperature=temperature,
            system_prompt=prompt,
            extra_tools=tools,
        )
