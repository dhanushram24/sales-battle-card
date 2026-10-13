import logging
from datetime import datetime, timezone
import hashlib
import json
from threading import Lock
from typing import Optional
from app.repositories.base import BaseLeadRepository
from app.services.analyzer import OpenAILeadAnalyzer
from app.schemas.battlecard import BattlecardResponse, BattlecardAIOutput
from app.core.config import settings

logger = logging.getLogger(__name__)
# Prevent overlapping analysis requests for a lead in this application process.
_analysis_locks = [Lock() for _ in range(64)]


class AnalysisRequiredError(RuntimeError):
    pass


class BattlecardService:
    def __init__(self, repo: BaseLeadRepository, analyzer: Optional[OpenAILeadAnalyzer] = None):
        self.repo = repo
        self.analyzer = analyzer or OpenAILeadAnalyzer()

    def get_battlecard(self, lead_id: str, force_refresh: bool = False, allow_analysis: bool = True) -> BattlecardResponse:
        lock = _analysis_locks[int(hashlib.sha256(lead_id.encode()).hexdigest(), 16) % len(_analysis_locks)]
        acquired = lock.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("Analysis is already running. Wait for it to finish, then retry.")
        try:
            return self._get_battlecard(lead_id, force_refresh, allow_analysis)
        finally:
            lock.release()

    def _get_battlecard(self, lead_id: str, force_refresh: bool, allow_analysis: bool) -> BattlecardResponse:
        """
        Retrieves the battlecard for a given lead.
        If force_refresh is False and a cached battlecard exists, returns the cached version.
        Otherwise, performs fresh semantic analysis with OpenAI and updates the cache.
        """
        lead = self.repo.get_lead_by_id(lead_id)
        if not lead:
            raise KeyError(f"Lead with ID '{lead_id}' not found in CRM.")

        interactions = self.repo.get_lead_interactions(lead_id)
        fingerprint = hashlib.sha256(json.dumps({
            "lead": lead.model_dump(mode="json", exclude={"interactions"}),
            "interactions": [i.model_dump(mode="json") for i in interactions],
            "model": settings.OPENAI_MODEL,
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

        # Cached analysis is only valid for the current profile, evidence and model.
        if not force_refresh:
            cached_data = self.repo.get_cached_battlecard(lead_id)
            if cached_data and cached_data.get("analysis_version") == "evidence-v2" and cached_data.get("source_fingerprint") == fingerprint:
                try:
                    return BattlecardResponse(**cached_data)
                except Exception as e:
                    logger.warning(f"Failed to deserialize cached battlecard for lead {lead_id}: {e}")

        if not allow_analysis:
            raise AnalysisRequiredError("No current score is saved for this lead. Select Generate score or Sync Battlecard to analyze its conversations.")

        # Fresh analysis via OpenAI
        ai_output: BattlecardAIOutput = self.analyzer.analyze_lead(lead, interactions)

        response = BattlecardResponse(
            **ai_output.model_dump(),
            lead_id=lead.id,
            lead_name=lead.name,
            company=lead.company,
            analyzed_interactions_count=len(interactions),
            last_synced_at=datetime.now(timezone.utc),
            source_fingerprint=fingerprint,
        )

        # Cache the result
        try:
            self.repo.save_battlecard(lead_id, response.model_dump())
        except Exception as e:
            response.cache_saved = False
            logger.error("Failed to persist battlecard cache (%s)", type(e).__name__)

        return response
