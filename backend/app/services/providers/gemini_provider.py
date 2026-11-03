import json
import logging
import urllib.request
import urllib.error
from typing import List
from app.core.config import settings
from app.schemas.lead import LeadInfo, LeadInteraction
from app.schemas.battlecard import (
    BattlecardAIOutput, BattlecardAnalysis, AnalysisMetrics, UsageReport
)
from app.services.providers.base import BaseLLMProvider, ProviderError

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini 1.5 Flash / Pro LLM Provider.
    Calls Gemini API with structured JSON output mode.
    """

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-1.5-flash"

    @property
    def name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_") and len(self.api_key) > 10)

    def analyze(
        self,
        lead: LeadInfo,
        interactions: List[LeadInteraction],
        transcript_text: str,
        compressed: bool,
        source_bytes: int
    ) -> BattlecardAIOutput:
        if not self.is_configured():
            raise ProviderError("Google Gemini API key is not configured.", "gemini", "unconfigured")

        from app.services.analyzer import SYSTEM_PROMPT, normalize_score_label

        prompt_text = f"""
{SYSTEM_PROMPT}

LEAD PROFILE:
- Lead ID: {lead.id}
- Name: {lead.name}
- Company: {lead.company}
- Current Status: {lead.status or 'N/A'}
- Pipeline Stage: {lead.stage or 'N/A'}
- Assigned Rep: {lead.assigned_to or 'N/A'}

CONVERSATION EVIDENCE ({len(interactions)} interactions; compressed={compressed}):
{transcript_text}

Respond ONLY with valid JSON conforming to the requested Sales Battlecard schema.
Schema keys: purchase_outlook, confidence, overall_score, classification, score_breakdown (sentiment_score, engagement_score, intent_score, risk_penalty), sentiment_summary, sentiment_trend, emotional_dimensions (trust_and_rapport, commercial_urgency, negotiation_stance), channel_sentiments, positive_drivers, friction_drivers, interaction_sentiments, buying_signals, objections, competitors, recommended_talk_tracks, next_best_action.
"""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        url = GEMINI_API_URL.format(model=self.model, key=self.api_key)
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error("Gemini API HTTP Error %s: %s", e.code, err_body)
            raise ProviderError(f"Gemini API returned HTTP {e.code}: {err_body[:200]}", "gemini", str(e.code)) from e
        except Exception as e:
            logger.error("Gemini request failed (%s)", type(e).__name__)
            raise ProviderError(f"Failed to connect to Google Gemini: {e}", "gemini", type(e).__name__) from e

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ProviderError("Gemini returned empty candidate list.", "gemini", "empty_response")
            raw_json_str = candidates[0]["content"]["parts"][0]["text"]
            parsed_dict = json.loads(raw_json_str)

            analysis = BattlecardAnalysis(**parsed_dict)
            result = BattlecardAIOutput(**analysis.model_dump())
            normalize_score_label(result)

            usage_meta = data.get("usageMetadata", {})
            in_tok = usage_meta.get("promptTokenCount")
            out_tok = usage_meta.get("candidatesTokenCount")

            result.evidence_summary = transcript_text if compressed else ""
            result.summary_compressed = compressed
            result.source_utf8_bytes = source_bytes
            result.scoring_evidence_utf8_bytes = len(transcript_text.encode("utf-8"))
            result.analysis_metrics = AnalysisMetrics(
                summary_mode="direct",
                summary_model=self.model,
                scoring_model=f"gemini:{self.model}",
                reused_interactions=0,
                summary_processed_utf8_bytes=source_bytes,
                summary_cache_saved=True,
                summary_usage=UsageReport(),
                scoring_usage=UsageReport(calls=1, input_tokens=in_tok, output_tokens=out_tok)
            )
            return result
        except Exception as e:
            logger.error("Failed to parse Gemini output: %s", e)
            raise ProviderError(f"Failed to parse Gemini structured response: {e}", "gemini", "parse_error") from e

