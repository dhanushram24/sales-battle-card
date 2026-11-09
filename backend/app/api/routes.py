import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.repositories.mysql_repo import MySQLLeadRepository, InteractionSourceError
from app.services.battlecard_service import BattlecardService, AnalysisRequiredError
from app.services.analyzer import OpenAILeadAnalyzer
from app.core.config import settings
from app.schemas.battlecard import (
    BattlecardResponse, DealSimulationRequest, DealSimulationResponse,
    PortfolioRadarResponse, PortfolioLeadSummary, ReengagementPackage,
    AccountDossier, AccountContactSummary
)
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

    from app.services.providers.router import LLMRouter
    ai_status = LLMRouter().get_status()
    return {
        "status": "healthy" if db_connected else "degraded",
        "database_connected": db_connected,
        "database_error": error_msg,
        "ai_engine": ai_status
    }


@router.get("/portfolio/radar", response_model=PortfolioRadarResponse)
def get_portfolio_radar(db: Session = Depends(get_db)):
    """
    Phase 3: Portfolio-wide deal health & slippage radar.
    Aggregates health across all pipeline deals to detect stalled momentum
    and forecast risks.
    """
    repo = MySQLLeadRepository(db)
    service = BattlecardService(repo=repo)
    try:
        leads_raw = db.execute(text(f"SELECT {settings.COL_LEAD_ID} AS id, {settings.COL_LEAD_NAME} AS name, {settings.COL_LEAD_COMPANY} AS company, {settings.COL_LEAD_STAGE} AS stage FROM {settings.TABLE_LEADS}")).mappings().all()
    except Exception as e:
        logger.error("Failed to query portfolio leads (%s)", type(e).__name__)
        raise HTTPException(status_code=503, detail="Unable to load portfolio leads.") from e

    portfolio_items = []
    total_score = 0.0
    healthy_count = 0
    at_risk_count = 0
    stalled_count = 0

    for l in leads_raw:
        lid = str(l["id"])
        name = l.get("name") or "Unnamed Contact"
        company = l.get("company") or "Unnamed Account"
        stage = l.get("stage") or "Discovery"

        try:
            card = service.get_battlecard(lead_id=lid, force_refresh=False, allow_analysis=True)
            score = card.overall_score or 5.0
            classification = card.classification or "Unclassified"
            momentum = card.momentum.momentum_direction if card.momentum else "steady"
        except Exception:
            score = 6.5
            classification = "Warm - Evaluating"
            momentum = "steady"

        total_score += score
        if score >= 7.5:
            healthy_count += 1
        elif score < 6.0:
            at_risk_count += 1

        if momentum == "stalled":
            stalled_count += 1

        is_closing_stage = any(s in stage.lower() for s in ["proposal", "negotiation", "review"])
        slippage = is_closing_stage and (score < 6.5 or momentum in ("decelerating", "stalled"))

        portfolio_items.append(PortfolioLeadSummary(
            lead_id=lid,
            name=name,
            company=company,
            stage=stage,
            score=round(score, 1),
            classification=classification,
            momentum=momentum,
            slippage_risk=slippage
        ))

    count = len(portfolio_items)
    avg_score = round(total_score / max(1, count), 1)

    return PortfolioRadarResponse(
        total_leads=count,
        average_health_score=avg_score,
        healthy_deals_count=healthy_count,
        at_risk_deals_count=at_risk_count,
        stalled_deals_count=stalled_count,
        leads=portfolio_items
    )


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


@router.post("/leads/{lead_id}/actions")
def log_rep_action(lead_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Logs a tactical talk track or action plan directly into CRM rep_thread."""
    note = (payload.get("note") or payload.get("content") or "").strip()
    if not note:
        raise HTTPException(status_code=400, detail="Action note cannot be empty.")
    repo = MySQLLeadRepository(db)
    try:
        lead = repo.get_lead_by_id(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")
        rep_name = lead.assigned_to or "Sales Rep"
        return repo.add_rep_action(lead_id, note, rep_name=rep_name)
    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Lead not found.") from e
    except Exception as e:
        logger.error("Failed to record rep action: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save action plan to CRM.") from e


@router.get("/leads/{lead_id}/sync-stream")
async def sync_battlecard_stream(lead_id: str, db: Session = Depends(get_db)):
    """
    Streams Server-Sent Events (SSE) detailing the step-by-step progress
    of omnichannel gathering, memory preparation, and multi-provider AI scoring.
    """
    repo = MySQLLeadRepository(db)
    lead = repo.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")

    async def event_generator():
        import asyncio
        try:
            yield f"event: progress\ndata: {json.dumps({'step': 'extracting', 'message': 'Gathering interactions across WhatsApp, CTI call logs, emails...', 'percent': 25})}\n\n"
            await asyncio.sleep(0.2)
            interactions = repo.get_lead_interactions(lead_id)

            yield f"event: progress\ndata: {json.dumps({'step': 'preparing', 'message': f'Aggregated {len(interactions)} omnichannel interactions. Validating evidence memory...', 'percent': 50})}\n\n"
            await asyncio.sleep(0.2)

            yield f"event: progress\ndata: {json.dumps({'step': 'analyzing', 'message': 'Running multi-provider AI engine for deal health, objections & competitor radar...', 'percent': 75})}\n\n"
            await asyncio.sleep(0.2)
            service = BattlecardService(repo=repo)
            battlecard = service.get_battlecard(lead_id=lead_id, force_refresh=True, allow_analysis=True)

            yield f"event: complete\ndata: {battlecard.model_dump_json()}\n\n"
        except Exception as e:
            logger.error("Streaming analysis failed for lead %s: %s", lead_id, e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/leads/{lead_id}/simulate", response_model=DealSimulationResponse)
def simulate_deal_scenario(lead_id: str, payload: DealSimulationRequest, db: Session = Depends(get_db)):
    """
    Phase 3: Interactive What-If Deal Strategy Simulator.
    Simulates deal health score trajectory and synthesizes a closing pitch
    script based on hypothetical commercial concessions.
    """
    repo = MySQLLeadRepository(db)
    lead = repo.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")

    service = BattlecardService(repo=repo)
    try:
        battlecard = service.get_battlecard(lead_id=lead_id, force_refresh=False, allow_analysis=True)
    except Exception:
        battlecard = service.get_battlecard(lead_id=lead_id, force_refresh=True, allow_analysis=True)

    base_score = battlecard.overall_score or 5.0
    score_delta = 0.0
    reaction_points = []
    concession_highlights = []

    # Evaluate discount
    if payload.discount_percent > 0:
        disc_impact = min(1.8, round(payload.discount_percent * 0.12, 1))
        score_delta += disc_impact
        concession_highlights.append(f"{payload.discount_percent}% licensing discount")
        reaction_points.append(f"Relieves commercial budget constraint (+{disc_impact} pts).")

    # Evaluate setup fee waiver
    if payload.waive_setup_fees:
        score_delta += 0.8
        concession_highlights.append("waived CTI telephony gateway setup fee")
        reaction_points.append("Lowers upfront friction for immediate IT stakeholder onboarding (+0.8 pts).")

    # Evaluate SLA guarantee
    if payload.guarantee_sla:
        score_delta += 1.0
        concession_highlights.append("contractually committed 99.9% uptime SLA")
        reaction_points.append("Mitigates enterprise reliability objections against competitors (+1.0 pts).")

    # Evaluate accelerated onboarding
    if payload.shorten_onboarding_days > 0:
        sprint_impact = min(0.7, round(payload.shorten_onboarding_days * 0.03, 1))
        score_delta += sprint_impact
        concession_highlights.append(f"guaranteed {payload.shorten_onboarding_days}-day accelerated rollout sprint")
        reaction_points.append(f"Accelerates time-to-value for operational teams (+{sprint_impact} pts).")

    if payload.custom_concession:
        score_delta += 0.5
        concession_highlights.append(f"custom concession ({payload.custom_concession})")
        reaction_points.append("Directly accommodates bespoke commercial requirement (+0.5 pts).")

    score_delta = round(score_delta, 1)
    simulated_score = round(min(9.9, max(1.0, base_score + score_delta)), 1)

    if simulated_score >= 8.5:
        simulated_outlook = "Hot - Ready to Close"
        tactic = "Execute mutual closing plan: deliver signed agreement with end-of-week incentive expiry."
    elif simulated_score >= 7.0:
        simulated_outlook = "Warm - High Closing Probability"
        tactic = "Present concession package directly to economic buyer and request final signature."
    else:
        simulated_outlook = "Evaluating - Needs Stakeholder Consensus"
        tactic = "Offer concessions contingent on multi-year commitment or seat expansion."

    # Dynamic closing pitch script
    concession_str = ", ".join(concession_highlights) if concession_highlights else "standard terms"
    closing_script = (
        f"\"Hi {lead.name or 'there'}, we reviewed {lead.company or 'your team'}'s requirements with our leadership. "
        f"To support your timeline and de-risk your deployment, we have approved {concession_str}. "
        f"With this in place, we can finalize the contract this week and initiate the technical onboarding sprint immediately.\""
    )

    buyer_reaction = " ".join(reaction_points) if reaction_points else "Baseline terms remain unchanged; deal readiness follows organic timeline."

    return DealSimulationResponse(
        lead_id=lead_id,
        base_score=base_score,
        simulated_score=simulated_score,
        score_delta=score_delta,
        simulated_outlook=simulated_outlook,
        projected_buyer_reaction=buyer_reaction,
        closing_pitch_script=closing_script,
        recommended_closing_tactic=tactic
    )


@router.post("/leads/{lead_id}/reengage", response_model=ReengagementPackage)
def generate_reengagement_package(lead_id: str, db: Session = Depends(get_db)):
    """
    Phase 4: Autonomous Deal Recovery Engine.
    Synthesizes an executive re-engagement package (email + agenda + concession)
    tailored to the lead's stalled momentum and specific objection.
    """
    repo = MySQLLeadRepository(db)
    lead = repo.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")

    service = BattlecardService(repo=repo)
    try:
        card = service.get_battlecard(lead_id=lead_id, force_refresh=False, allow_analysis=True)
    except Exception:
        card = service.get_battlecard(lead_id=lead_id, force_refresh=True, allow_analysis=True)

    score = card.overall_score or 5.0
    days_since_touch = card.momentum.days_since_last_customer_touch if card.momentum else 3
    stall_risk = card.momentum.stall_risk_level if card.momentum else "Moderate"
    top_objection = card.objections[0].objection if card.objections else "Commercial verification"
    primary_competitor = card.competitors[0].competitor_name if card.competitors else "competing solutions"

    if stall_risk.lower() in ("high", "critical (ghosting)") or score < 6.0:
        urgency = "Critical"
    elif days_since_touch > 5 or score < 7.5:
        urgency = "Elevated"
    else:
        urgency = "Standard"

    headline = f"Executive Intervention for {lead.company}: Overcoming '{top_objection[:60]}'"
    subject = f"Executive Alignment: Paramantra CRM Rollout & Commercial Review — {lead.company}"

    email_body = (
        f"Dear {lead.name},\n\n"
        f"I am reaching out directly from our executive team regarding {lead.company}'s CRM evaluation. "
        f"Our solutions team noted your specific requirement regarding: \"{top_objection}\".\n\n"
        f"We recognize the critical operational priorities for your team. To ensure this deployment delivers immediate "
        f"ROI without administrative friction, we would welcome a 15-minute executive briefing call to review approved "
        f"commercial accommodations and confirm dedicated onboarding milestones.\n\n"
        f"Would you or your leadership team have availability this Thursday or Friday for a brief call?\n\n"
        f"Warm regards,\n"
        f"Sales Leadership | Paramantra"
    )

    agenda = [
        f"Review executive ROI and eliminate third-party connector fees versus {primary_competitor}.",
        f"Address specific objection: '{top_objection[:80]}'.",
        "Present guaranteed 30-day technical onboarding sprint with dedicated solutions lead."
    ]

    concession = "Offer waived CTI gateway setup fees and committed 99.9% uptime SLA addendum."

    return ReengagementPackage(
        lead_id=lead_id,
        recipient_name=lead.name or "Contact",
        recipient_company=lead.company or "Organization",
        urgency_level=urgency,
        intervention_headline=headline,
        email_subject=subject,
        email_body=email_body,
        executive_call_agenda=agenda,
        recommended_concession=concession
    )


@router.get("/accounts", response_model=List[AccountDossier])
def list_accounts(db: Session = Depends(get_db)):
    """
    Phase 4: Multi-contact enterprise account intelligence.
    Groups CRM opportunities by account, aggregating collective health and
    stakeholder alignment across the buying organization.
    """
    repo = MySQLLeadRepository(db)
    service = BattlecardService(repo=repo)
    try:
        leads_raw = db.execute(text(f"""
            SELECT {settings.COL_LEAD_ID} AS id, {settings.COL_LEAD_NAME} AS name,
                   {settings.COL_LEAD_COMPANY} AS company, {settings.COL_LEAD_STATUS} AS status,
                   {settings.COL_LEAD_STAGE} AS stage, {settings.COL_LEAD_ASSIGNED_TO} AS assigned_to
            FROM {settings.TABLE_LEADS}
        """)).mappings().all()
    except Exception as e:
        logger.error("Failed to query accounts (%s)", type(e).__name__)
        raise HTTPException(status_code=503, detail="Unable to load accounts.") from e

    companies: Dict[str, List[Any]] = {}
    for r in leads_raw:
        comp = (r.get("company") or "Independent Accounts").strip()
        companies.setdefault(comp, []).append(r)

    account_dossiers = []
    for comp_name, comp_leads in companies.items():
        contacts = []
        total_score = 0.0
        all_objections = []
        competitors = []

        for lead_row in comp_leads:
            lid = str(lead_row["id"])
            try:
                card = service.get_battlecard(lead_id=lid, force_refresh=False, allow_analysis=True)
                score = card.overall_score or 5.0
                for obj in card.objections:
                    if obj.objection not in all_objections:
                        all_objections.append(obj.objection)
                for c in card.competitors:
                    if c.competitor_name not in competitors:
                        competitors.append(c.competitor_name)
            except Exception:
                score = 6.5

            total_score += score
            contacts.append(AccountContactSummary(
                lead_id=lid,
                name=lead_row.get("name") or "Unnamed Contact",
                role="Stakeholder" if "cto" not in (lead_row.get("name") or "").lower() else "Technical Evaluator",
                stage=lead_row.get("stage") or "Discovery",
                status=lead_row.get("status") or "In Progress",
                assigned_to=lead_row.get("assigned_to") or "Unassigned",
                score=round(score, 1)
            ))

        avg_score = round(total_score / max(1, len(comp_leads)), 1)
        if avg_score >= 8.0:
            classification = "High-Readiness Enterprise Account"
        elif avg_score >= 6.5:
            classification = "Active Multi-Threaded Evaluation"
        else:
            classification = "At-Risk Account Requiring Executive Intervention"

        risk_summary = (
            f"Account comprises {len(contacts)} stakeholder contact(s) across "
            f"{len(set(c.stage for c in contacts))} pipeline stage(s). "
            f"Collective deal health stands at {avg_score}/10."
        )

        account_dossiers.append(AccountDossier(
            company_name=comp_name,
            total_contacts=len(contacts),
            collective_health_score=avg_score,
            account_classification=classification,
            primary_competitor=competitors[0] if competitors else None,
            active_objections=all_objections[:3],
            contacts=contacts,
            account_risk_summary=risk_summary
        ))

    account_dossiers.sort(key=lambda a: a.collective_health_score, reverse=True)
    return account_dossiers
