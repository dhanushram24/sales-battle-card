import logging
from typing import List, Dict, Any, Optional
from openai import AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError
from app.core.config import settings
from app.schemas.lead import LeadInfo, LeadInteraction
from app.schemas.battlecard import BattlecardAIOutput
from app.services.usage import TokenUsage
from app.services.providers.base import BaseLLMProvider, ProviderError
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.offline_provider import OfflineHeuristicProvider

logger = logging.getLogger(__name__)


def is_provider_infrastructure_error(error: Exception) -> bool:
    """Check if error is an auth, network, or quota failure eligible for failover."""
    cause = getattr(error, "__cause__", None) or error
    if isinstance(cause, (AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    msg = str(error).lower()
    return any(keyword in msg for keyword in ("credentials", "expired_secret_key", "quota", "cannot connect", "rate limit"))


class LLMRouter:
    """
    Intelligent router and failover orchestrator for LLM providers.
    Ensures sales battlecards can always be generated even if an external
    provider's key has expired or rate limits have been exceeded.
    """

    def __init__(self, openai_client: Optional[Any] = None):
        self.openai = OpenAIProvider(client=openai_client)
        self.gemini = GeminiProvider()
        self.offline = OfflineHeuristicProvider()

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured_mode": settings.AI_PROVIDER,
            "allow_offline_fallback": settings.ALLOW_OFFLINE_FALLBACK,
            "openai": {
                "configured": self.openai.is_configured(),
                "model": settings.OPENAI_MODEL
            },
            "gemini": {
                "configured": self.gemini.is_configured(),
                "model": settings.GEMINI_MODEL
            },
            "offline_heuristic": {
                "available": True
            }
        }

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
        mode = (settings.AI_PROVIDER or "auto").lower()

        # 1. Explicit offline mode
        if mode == "offline":
            logger.info("Executing offline heuristic analysis for lead %s (configured mode=offline)", lead.id)
            return self.offline.analyze(lead, interactions, transcript_text, compressed, source_bytes)

        errors = []

        # 2. Try OpenAI
        if mode in ("auto", "openai"):
            if self.openai.is_configured() or self.openai.client is not None:
                try:
                    logger.info("Attempting analysis for lead %s with OpenAI (%s)", lead.id, settings.OPENAI_MODEL)
                    return self.openai.analyze(
                        lead, interactions, transcript_text, compressed, source_bytes,
                        evidence_mode=evidence_mode, reused_interactions=reused_interactions,
                        processed_bytes=processed_bytes, summary_usage=summary_usage,
                        summary_model=summary_model
                    )
                except Exception as e:
                    if settings.ALLOW_OFFLINE_FALLBACK and is_provider_infrastructure_error(e):
                        logger.warning("OpenAI provider infrastructure error (%s); eligible for failover.", e)
                        errors.append(f"OpenAI: {e}")
                    else:
                        raise
            elif mode == "openai" and not settings.ALLOW_OFFLINE_FALLBACK:
                raise RuntimeError("OpenAI is configured as the required provider, but OPENAI_API_KEY is missing or invalid.")

        # 3. Try Google Gemini
        if mode in ("auto", "gemini"):
            if self.gemini.is_configured():
                try:
                    logger.info("Attempting analysis for lead %s with Google Gemini (%s)", lead.id, settings.GEMINI_MODEL)
                    return self.gemini.analyze(lead, interactions, transcript_text, compressed, source_bytes)
                except Exception as e:
                    if settings.ALLOW_OFFLINE_FALLBACK and is_provider_infrastructure_error(e):
                        logger.warning("Google Gemini provider error (%s); eligible for failover.", e)
                        errors.append(f"Gemini: {e}")
                    else:
                        raise
            elif mode == "gemini" and not settings.ALLOW_OFFLINE_FALLBACK:
                raise RuntimeError("Google Gemini is configured as the required provider, but GEMINI_API_KEY is missing.")

        # 4. Fallback to Offline Heuristic Analyzer if allowed and errors occurred
        if settings.ALLOW_OFFLINE_FALLBACK and errors:
            reason = "; ".join(errors)
            logger.info("Failing over to Offline Heuristic Engine for lead %s. Reason: %s", lead.id, reason)
            result = self.offline.analyze(lead, interactions, transcript_text, compressed, source_bytes)
            result.sentiment_summary += " [Note: Heuristic fallback active due to provider credentials/quota issue]."
            return result

        # 5. If fallback is disabled and all options failed, raise error
        error_summary = " | ".join(errors) if errors else "No LLM provider was available."
        raise RuntimeError(f"Analysis failed and offline fallback is disabled. Details: {error_summary}")
