import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.repositories.mysql_repo import MySQLLeadRepository, InteractionSourceError
from app.services.battlecard_service import BattlecardService, AnalysisRequiredError
from app.services.analyzer import OpenAILeadAnalyzer
from app.core.config import settings
from app.schemas.battlecard import BattlecardResponse
from app.schemas.lead import LeadInfo, LeadUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Battlecard"])


def get_battlecard_service(db: Session = Depends(get_db)) -> BattlecardService:
    repo = MySQLLeadRepository(db)
    return BattlecardService(repo=repo)


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint checking application and MySQL DB connection."""
    db_connected = False
    error_msg = None
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        error_msg = "Database connection failed. Check backend configuration."

    return {
        "status": "healthy" if db_connected else "degraded",
        "database_connected": db_connected,
        "database_error": error_msg
    }


@router.get("/leads")
def list_leads(db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200)):
    """Returns list of leads available in CRM for quick switching in UI."""
    try:
        query = text(f"SELECT {settings.COL_LEAD_ID} AS id, {settings.COL_LEAD_NAME} AS name, {settings.COL_LEAD_COMPANY} AS company, {settings.COL_LEAD_STATUS} AS status, {settings.COL_LEAD_STAGE} AS stage, {settings.COL_LEAD_ASSIGNED_TO} AS assigned_to FROM {settings.TABLE_LEADS} ORDER BY {settings.COL_LEAD_ID} LIMIT :limit OFFSET :offset")
        rows = db.execute(query, {"limit": limit, "offset": offset}).mappings().all()
        return [{**dict(r), "id": str(r["id"])} for r in rows]
    except Exception as e:
        logger.error("Failed to list leads (%s)", type(e).__name__)
        raise HTTPException(status_code=503, detail="Unable to load leads. Check the database connection and configured columns.") from e


@router.get("/leads/{lead_id}/timeline")
def get_lead_timeline(lead_id: str, db: Session = Depends(get_db)):
    """Returns lead profile information along with all historical omnichannel interactions."""
    repo = MySQLLeadRepository(db)
    lead = repo.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lead {lead_id} not found.")
    try:
        interactions = repo.get_lead_interactions(lead_id)
    except InteractionSourceError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {
        "lead": lead,
        "interactions": interactions,
        "total_interactions": len(interactions)
    }


@router.get("/leads/{lead_id}/battlecard", response_model=BattlecardResponse)
def get_lead_battlecard(
    lead_id: str,
    service: BattlecardService = Depends(get_battlecard_service)
):
    """
    Fetch the battlecard and 0-10 score for a lead.
    Returns a valid cached analysis. Use POST /sync to generate a new score.
    """
    try:
        return service.get_battlecard(lead_id=lead_id, allow_analysis=False)
    except AnalysisRequiredError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to generate battlecard (%s)", type(e).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis failed. Check backend logs for the error type.")


@router.post("/leads/{lead_id}/sync", response_model=BattlecardResponse)
def sync_lead_battlecard(
    lead_id: str,
    service: BattlecardService = Depends(get_battlecard_service)
):
    """
    Triggered by the 'Sync' button in Paramantra CRM.
    Forces fresh semantic analysis across all current notes/interactions and updates cache.
    """
    try:
        return service.get_battlecard(lead_id=lead_id, force_refresh=True)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to sync battlecard (%s)", type(e).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis failed. Check backend logs for the error type.")


@router.post("/leads/test-analyze", response_model=BattlecardResponse)
def test_analyze_direct(lead: LeadInfo):
    """
    Direct test endpoint: send a LeadInfo payload with interactions directly
    in the request body to test semantic scoring and OpenAI battlecard output
    without querying MySQL.
    """
    if not settings.ENABLE_TEST_ANALYZE:
        raise HTTPException(status_code=404, detail="Test analysis endpoint is disabled.")
    try:
        analyzer = OpenAILeadAnalyzer()
        ai_output = analyzer.analyze_lead(lead, lead.interactions)
        return BattlecardResponse(
            lead_id=lead.id,
            lead_name=lead.name,
            company=lead.company,
            **ai_output.model_dump(),
            analyzed_interactions_count=len(lead.interactions),
            last_synced_at=datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error("Direct test analysis failed (%s)", type(e).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis failed. Check backend logs for the error type.")


@router.patch("/leads/{lead_id}", response_model=LeadInfo)
def update_lead(lead_id: str, changes: LeadUpdate, db: Session = Depends(get_db)):
    try:
        return MySQLLeadRepository(db).update_lead(lead_id, changes)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Lead not found.") from e
