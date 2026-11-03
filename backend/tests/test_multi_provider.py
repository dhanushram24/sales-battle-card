import unittest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from openai import AuthenticationError
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.lead import LeadInfo, LeadInteraction
from app.services.providers.offline_provider import OfflineHeuristicProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.router import LLMRouter, is_provider_infrastructure_error
from app.core.config import settings


class MultiProviderTests(unittest.TestCase):
    def setUp(self):
        self.lead = LeadInfo(
            id="test-lead-1",
            name="Ananya Verma",
            company="Tata Digital",
            status="In Progress",
            stage="Proposal Under Review",
            assigned_to="Karan rep"
        )
        self.interactions = [
            LeadInteraction(
                id="1",
                lead_id="test-lead-1",
                content="We are looking for a complete CRM with telephony CTI integration.",
                interaction_type="whatsapp",
                direction="inbound",
                created_at=datetime.now(timezone.utc)
            ),
            LeadInteraction(
                id="2",
                lead_id="test-lead-1",
                content="Client evaluated Salesforce but found connector costs too expensive. Very keen on our automation proposal.",
                interaction_type="call",
                direction="outbound",
                created_at=datetime.now(timezone.utc)
            ),
            LeadInteraction(
                id="3",
                lead_id="test-lead-1",
                content="Please share the proposal. Need confirmation on deployment SLA within 30 days.",
                interaction_type="email",
                direction="inbound",
                created_at=datetime.now(timezone.utc)
            ),
        ]

    def test_offline_heuristic_provider_produces_complete_battlecard(self):
        provider = OfflineHeuristicProvider()
        result = provider.analyze(
            self.lead,
            self.interactions,
            transcript_text="sample",
            compressed=False,
            source_bytes=500
        )
        self.assertGreaterEqual(result.overall_score, 0.0)
        self.assertLessEqual(result.overall_score, 10.0)
        self.assertIn("Tata Digital", result.sentiment_summary)
        self.assertEqual(result.analysis_metrics.summary_mode, "offline_heuristic")

        # Competitor detection
        self.assertTrue(any(c.competitor_name == "Salesforce Service Cloud" for c in result.competitors))
        # Objections detection
        self.assertTrue(any("sla" in o.objection.lower() or "timeline" in o.objection.lower() for o in result.objections))
        # Positive drivers
        self.assertGreater(len(result.positive_drivers), 0)
        # Emotional stance
        self.assertIn(result.emotional_dimensions.negotiation_stance, ("Collaborative", "Ready to Sign", "Hard Bargaining"))

    def test_gemini_provider_unconfigured_check(self):
        provider = GeminiProvider(api_key="")
        self.assertFalse(provider.is_configured())

    def test_infrastructure_error_detection(self):
        auth_err = AuthenticationError("Invalid API key", response=Mock(status_code=401), body=None)
        self.assertTrue(is_provider_infrastructure_error(auth_err))
        normal_err = RuntimeError("Something unexpected")
        self.assertFalse(is_provider_infrastructure_error(normal_err))

    def test_router_falls_back_to_offline_on_auth_failure(self):
        with patch.object(settings, "AI_PROVIDER", "auto"):
            with patch.object(settings, "ALLOW_OFFLINE_FALLBACK", True):
                with patch.object(settings, "OPENAI_API_KEY", "test-key"):
                    router = LLMRouter()
                    auth_err = AuthenticationError("Your API key has expired", response=Mock(status_code=401), body=None)
                    router.openai.client = Mock()
                    router.openai.client.beta.chat.completions.parse.side_effect = auth_err

                    result = router.analyze(
                        self.lead,
                        self.interactions,
                        transcript_text="sample transcript",
                        compressed=False,
                        source_bytes=300
                    )
                    self.assertEqual(result.analysis_metrics.summary_mode, "offline_heuristic")
                    self.assertIn("fallback", result.sentiment_summary.lower())

    def test_actions_endpoint_validates_and_rejects_empty_payload(self):
        client = TestClient(app)
        resp = client.post("/api/leads/123/actions", json={"note": ""})
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
