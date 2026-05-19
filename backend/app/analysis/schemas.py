import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AnalysisJobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
AnalysisClassification = Literal[
    "book",
    "best",
    "excellent",
    "good",
    "inaccuracy",
    "mistake",
    "blunder",
    "forced",
    "unknown",
]


class AnalysisRequest(BaseModel):
    depth: int | None = Field(default=None, ge=1)


class AnalysisJobResponse(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    status: AnalysisJobStatus
    engine_name: str
    engine_version: str | None
    depth: int | None
    time_limit_ms: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisJobListResponse(BaseModel):
    items: list[AnalysisJobResponse]
    limit: int
    offset: int
    total: int


class AnalysisMoveEvaluationResponse(BaseModel):
    id: uuid.UUID | None = None
    game_move_id: uuid.UUID | None = None
    ply_number: int
    move_number: int | None = None
    side: str
    san: str
    uci: str
    evaluation_before: dict[str, Any] | None
    evaluation_after: dict[str, Any] | None
    best_move_uci: str | None
    best_move_san: str | None
    principal_variation: list[str] | None
    centipawn_loss: int | None
    classification: AnalysisClassification | None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisReportSummaryResponse(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    analysis_job_id: uuid.UUID
    white_accuracy: float | None
    black_accuracy: float | None
    summary: dict[str, Any]
    final_evaluation: dict[str, Any] | None
    created_at: datetime

    @field_validator("white_accuracy", "black_accuracy", mode="before")
    @classmethod
    def decimal_to_float(cls, value: Decimal | float | None) -> float | None:
        if value is None:
            return None
        return float(value)

    model_config = ConfigDict(from_attributes=True)


class AnalysisReportResponse(AnalysisReportSummaryResponse):
    moves: list[AnalysisMoveEvaluationResponse]


class AnalysisReportListResponse(BaseModel):
    items: list[AnalysisReportSummaryResponse]
    limit: int
    offset: int
    total: int


class GameAnalysisResponse(BaseModel):
    report: AnalysisReportResponse | None = None
    job: AnalysisJobResponse | None = None
