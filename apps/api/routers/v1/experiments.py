from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import APIKey
from models.schemas import ExperimentCreateRequest, ExperimentResponse
from services.experiment_service import experiment_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Experiments")
router = APIRouter(prefix="/experiments", tags=["Public API — Experiments"])

@router.get("", response_model=List[ExperimentResponse])
async def list_experiments(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("EXPERIMENT_READ"))
):
    """Lists A/B content experimentation tests."""
    experiments = await experiment_service.list_experiments(db)
    return [ExperimentResponse.model_validate(e) for e in experiments]

@router.post("", response_model=ExperimentResponse)
async def create_experiment(
    req: ExperimentCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("EXPERIMENT_WRITE"))
):
    """Creates a new A/B experiment test."""
    exp = await experiment_service.create_experiment(
        db, title=req.title, hypothesis=req.hypothesis, metric_name=req.metric_name, variants=[v.model_dump() for v in req.variants]
    )
    return ExperimentResponse.model_validate(exp)

@router.get("/{id}", response_model=ExperimentResponse)
async def get_experiment_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("EXPERIMENT_READ"))
):
    """Gets experiment detail with statistical Z-test math."""
    exp = await experiment_service.get_experiment(db, id)
    if not exp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Experiment '{id}' not found."}})
    return ExperimentResponse.model_validate(exp)

@router.post("/{id}/start")
async def start_experiment(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("EXPERIMENT_WRITE"))
):
    """Starts A/B test data collection."""
    res = await experiment_service.start_experiment(db, id)
    return res

@router.post("/{id}/stop")
async def stop_experiment(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("EXPERIMENT_WRITE"))
):
    """Stops experiment and declares statistical winner."""
    res = await experiment_service.stop_experiment(db, id)
    return res
