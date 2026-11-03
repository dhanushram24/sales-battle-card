import json
import logging
from typing import List, Optional, Any
from openai import OpenAI
from app.core.config import settings
from app.schemas.lead import LeadInfo, LeadInteraction
from app.schemas.battlecard import (
    BattlecardAIOutput, BattlecardAnalysis, AnalysisMetrics, UsageReport
)
from app.services.usage import TokenUsage
from app.services.providers.base import BaseLLMProvider, ProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI Provider utilizing Structured Outputs (gpt-4o / gpt-4o-mini).
    """

    def __init__(self, api_key: str = "", model: str = "", client: Optional[Any] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.client = client or OpenAI(api_key=self.api_key or "dummy-key", timeout=60.0, max_retries=1)

    @property
    def name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_") and len(self.api_key) > 10)

    def analyze(
        self,
        lead: LeadInfo,
        interactions: List[LeadInteraction],
        transcript_text: str,
        compressed: bool,
        source_bytes: int,
        evidence_mode: str = "direct",
        reused_interactions: int = 0,
        processed_bytes: int = 0,
        summary_usage: Optional[TokenUsage] = None,
        summary_model: str = ""
    ) -> BattlecardAIOutput:
        from app.services.analyzer import SYSTEM_PROMPT, normalize_score_label

        user_content = f"""
LEAD PROFILE:
- Lead ID: {lead.id}
- Name: {lead.name}
- Company: {lead.company}
- Current Status: {lead.status or 'N/A'}
- Pipeline Stage: {lead.stage or 'N/A'}
- Assigned Rep: {lead.assigned_to or 'N/A'}

CONVERSATION EVIDENCE ({len(interactions)} interactions; compressed={compressed}; original indices preserved):
{transcript_text}

Perform deep semantic analysis with exact quote attribution, per-interaction scoring, emotional dimensions decomposition, and tactical battlecard generation following the required schema.
"""
        scoring_usage = TokenUsage()
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                response_format=BattlecardAnalysis,
                max_completion_tokens=5000,
                temperature=0.2
            )
            scoring_usage.record(completion)
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise RuntimeError("OpenAI returned no valid analysis; no score was generated.")

            result = BattlecardAIOutput(**parsed.model_dump())
            normalize_score_label(result)

            retained_evidence = "\n".join(json.loads(transcript_text).values()) if compressed else transcript_text
            for field in ("positive_drivers", "friction_drivers"):
                setattr(result, field, [driver for driver in getattr(result, field)
                    if driver.quote and driver.quote in retained_evidence and any(driver.quote in item.content for item in interactions)])

            result.interaction_sentiments = [tag for tag in result.interaction_sentiments
                if 1 <= tag.interaction_idx <= len(interactions) and
                (not compressed or (tag.key_phrase and tag.key_phrase in retained_evidence and tag.key_phrase in interactions[tag.interaction_idx - 1].content))][:20]
            for tag in result.interaction_sentiments:
                if tag.key_phrase and tag.key_phrase not in interactions[tag.interaction_idx - 1].content:
                    tag.key_phrase = None

            result.evidence_summary = transcript_text if compressed else ""
            result.summary_compressed = compressed
            result.source_utf8_bytes = source_bytes
            result.scoring_evidence_utf8_bytes = len(transcript_text.encode("utf-8"))
            result.analysis_metrics = AnalysisMetrics(
                summary_mode=evidence_mode,
                summary_model=summary_model or self.model,
                scoring_model=self.model,
                reused_interactions=reused_interactions,
                summary_processed_utf8_bytes=processed_bytes,
                summary_cache_saved=True,
                summary_usage=summary_usage.as_dict() if summary_usage else UsageReport(),
                scoring_usage=scoring_usage.as_dict()
            )
            return result
        except Exception as e:
            from app.services.analyzer import analysis_error_message
            msg = analysis_error_message(e)
            logger.error("OpenAI analysis failed for lead %s (%s)", lead.id, type(e).__name__)
            raise RuntimeError(msg) from e
