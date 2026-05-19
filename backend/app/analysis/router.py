import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.schemas import (
    AnalysisJobListResponse,
    AnalysisJobResponse,
    AnalysisReportListResponse,
    AnalysisReportResponse,
    AnalysisRequest,
    GameAnalysisResponse,
)
from app.analysis.services import (
    get_analysis_job,
    get_analysis_report,
    get_game_analysis,
    list_admin_analysis_jobs,
    list_admin_analysis_reports,
    request_game_analysis,
)
from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db_session
from app.users.models import User

router = APIRouter(tags=["analysis"])


@router.post(
    "/games/{game_id}/analysis",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_game_analysis(
    game_id: uuid.UUID,
    payload: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobResponse:
    return await request_game_analysis(
        session=session,
        user=current_user,
        game_id=game_id,
        depth=payload.depth,
    )


@router.get("/analysis/jobs/{job_id}", response_model=AnalysisJobResponse)
async def analysis_job_detail(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobResponse:
    return await get_analysis_job(session=session, user=current_user, job_id=job_id)


@router.get("/games/{game_id}/analysis", response_model=GameAnalysisResponse)
async def game_analysis(
    game_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GameAnalysisResponse:
    return await get_game_analysis(session=session, user=current_user, game_id=game_id)


@router.get("/analysis/reports/{report_id}", response_model=AnalysisReportResponse)
async def analysis_report_detail(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisReportResponse:
    return await get_analysis_report(session=session, user=current_user, report_id=report_id)


@router.get("/admin/analysis/jobs", response_model=AnalysisJobListResponse)
async def admin_analysis_jobs(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    game_id: uuid.UUID | None = None,
    requested_by: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AnalysisJobListResponse:
    _ = current_admin
    return await list_admin_analysis_jobs(
        session=session,
        status_filter=status_filter,
        game_id=game_id,
        requested_by=requested_by,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/analysis/reports", response_model=AnalysisReportListResponse)
async def admin_analysis_reports(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    game_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AnalysisReportListResponse:
    _ = current_admin
    return await list_admin_analysis_reports(
        session=session,
        game_id=game_id,
        limit=limit,
        offset=offset,
    )
