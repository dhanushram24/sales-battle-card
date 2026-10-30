import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.core.database import get_db
from app.core.config import settings, Settings
from app.schemas.lead import LeadInfo, LeadInteraction, LeadUpdate
from app.schemas.battlecard import BattlecardAIOutput
from app.repositories.mysql_repo import MySQLLeadRepository, InteractionSourceError
from app.services.battlecard_service import BattlecardService, AnalysisRequiredError
from app.services.analyzer import analysis_error_message
from openai import APIConnectionError, AuthenticationError, RateLimitError, APITimeoutError
try:
    import httpx
except ImportError:
    import httpx2 as httpx


def output():
    return BattlecardAIOutput(overall_score=0, classification='At risk',
        score_breakdown=dict(sentiment_score=0, engagement_score=0, intent_score=0, risk_penalty=0),
        emotional_dimensions=dict(trust_and_rapport=0, commercial_urgency=0, negotiation_stance='Unknown'),
        sentiment_summary='No buying intent.', sentiment_trend='Stable', next_best_action='Confirm needs.')


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
        self.sessions = sessionmaker(bind=self.engine)
        with self.engine.begin() as db:
            db.execute(text('CREATE TABLE leads (id INTEGER PRIMARY KEY, name TEXT, company TEXT, status TEXT, stage TEXT, assigned_to TEXT)'))
            db.execute(text("INSERT INTO leads VALUES (1, 'Test Contact', 'Test Co', 'Active', 'Discovery', 'Rep')"))
            db.execute(text('CREATE TABLE lead_interactions (id INTEGER, lead_id INTEGER, notes TEXT, interaction_type TEXT, direction TEXT, created_at TEXT)'))
            db.execute(text("INSERT INTO lead_interactions VALUES (1, 1, 'Need approval', 'email', 'inbound', '2026-01-01 12:00:00')"))
        def database():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = database
        self.patches = [patch.object(settings, 'AUTH_USERNAME', ''), patch.object(settings, 'AUTH_PASSWORD', ''),
                        patch.object(settings, 'INTERACTION_SOURCES', 'generic'), patch.object(settings, 'ENABLE_TEST_ANALYZE', False)]
        for item in self.patches: item.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        for item in reversed(self.patches): item.stop()
        self.engine.dispose()

    def test_edit_persists_and_sql_values_are_bound(self):
        value = "O'Brien; DROP TABLE leads; --"
        response = self.client.patch('/api/leads/1', json={'name': value, 'stage': 'Negotiation'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/leads/1/timeline').json()['lead']['name'], value)
        self.assertEqual(self.client.get('/api/leads').json()[0]['stage'], 'Negotiation')

    def test_empty_null_and_unknown_updates_rejected(self):
        for payload in [{}, {'name': ' '}, {'name': None}, {'id': '2'}, {'company': 'x' * 151}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch('/api/leads/1', json=payload).status_code, 422)
        self.assertEqual(self.client.patch('/api/leads/2', json={'name': 'Missing'}).status_code, 404)

    def test_list_pagination_and_string_ids(self):
        self.assertEqual(self.client.get('/api/leads?limit=1').json()[0]['id'], '1')
        self.assertEqual(self.client.get('/api/leads?offset=1').json(), [])
        self.assertEqual(self.client.get('/api/leads?limit=999').status_code, 422)

    def test_configured_source_failure_blocks_analysis(self):
        with patch.object(settings, 'INTERACTION_SOURCES', 'whats_app'):
            result = self.client.get('/api/leads/1/timeline')
            self.assertEqual(result.status_code, 503)
            self.assertIn('whats_app', result.json()['detail'])

    def test_database_failure_is_not_an_empty_lead_list(self):
        with self.engine.begin() as db: db.execute(text('DROP TABLE leads'))
        self.assertEqual(self.client.get('/api/leads').status_code, 503)

    def test_no_paid_analysis_on_get_or_disabled_test_route(self):
        with patch('app.services.battlecard_service.OpenAILeadAnalyzer') as analyzer:
            self.assertEqual(self.client.get('/api/leads/1/battlecard').status_code, 409)
            analyzer.return_value.analyze_lead.assert_not_called()
        self.assertEqual(self.client.post('/api/leads/test-analyze', json={'id': 'test'}).status_code, 404)

    def test_authentication_covers_dashboard_and_api(self):
        with patch.object(settings, 'AUTH_USERNAME', 'operator'), patch.object(settings, 'AUTH_PASSWORD', 'test-password-long'):
            for path in ['/', '/api/leads', '/docs']:
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertIn('WWW-Authenticate', response.headers)
            self.assertEqual(self.client.get('/api/leads', auth=('operator', 'incorrect')).status_code, 401)
            self.assertEqual(self.client.get('/api/leads', auth=('operator', 'test-password-long')).status_code, 200)

    def test_remote_anonymous_access_and_cross_origin_writes_denied(self):
        with TestClient(app, client=('203.0.113.5', 1234)) as remote:
            self.assertEqual(remote.get('/api/leads').status_code, 403)
        self.assertEqual(self.client.patch('/api/leads/1', json={'name': 'Changed'}, headers={'Origin': 'https://untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.patch('/api/leads/1', json={'name': 'Changed'}, headers={'Origin': 'http://localhost:5173'}).status_code, 200)

    def test_malformed_auth_does_not_crash(self):
        with patch.object(settings, 'AUTH_USERNAME', 'operator'), patch.object(settings, 'AUTH_PASSWORD', 'test-password-long'):
            self.assertEqual(self.client.get('/api/leads', headers={'Authorization': 'Basic ###'}).status_code, 401)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.repo.get_lead_by_id.return_value = LeadInfo(id='1', name='Test')
        self.repo.get_lead_interactions.return_value = [LeadInteraction(id='1', lead_id='1', content='Not buying')]
        self.repo.get_cached_battlecard.return_value = None
        self.analyzer = Mock()
        self.analyzer.analyze_lead.return_value = output()
        self.service = BattlecardService(self.repo, self.analyzer)

    def test_valid_cache_avoids_api_and_zero_is_preserved(self):
        first = self.service.get_battlecard('1')
        self.repo.get_cached_battlecard.return_value = first.model_dump()
        second = self.service.get_battlecard('1', allow_analysis=False)
        self.assertEqual(second.overall_score, 0)
        self.assertEqual(self.analyzer.analyze_lead.call_count, 1)

    def test_new_evidence_and_profile_invalidate_cached_score(self):
        first = self.service.get_battlecard('1')
        self.repo.get_cached_battlecard.return_value = first.model_dump()
        self.repo.get_lead_interactions.return_value.append(LeadInteraction(id='2', lead_id='1', content='Now buying'))
        with self.assertRaises(AnalysisRequiredError): self.service.get_battlecard('1', allow_analysis=False)
        self.repo.get_lead_interactions.return_value.pop()
        self.repo.get_lead_by_id.return_value.stage = 'Closed Won'
        with self.assertRaises(AnalysisRequiredError): self.service.get_battlecard('1', allow_analysis=False)

    def test_scoring_prompt_change_invalidates_cached_score(self):
        first = self.service.get_battlecard('1')
        self.repo.get_cached_battlecard.return_value = first.model_dump()
        with patch('app.services.battlecard_service.ANALYSIS_VERSION', 'changed-prompt'):
            with self.assertRaises(AnalysisRequiredError):
                self.service.get_battlecard('1', allow_analysis=False)
        self.assertEqual(self.analyzer.analyze_lead.call_count, 1)

    def test_failed_cache_write_reported_to_ui(self):
        self.repo.save_battlecard.side_effect = RuntimeError('DB unavailable')
        self.assertFalse(self.service.get_battlecard('1').cache_saved)

    def test_failed_analysis_does_not_cache_or_leave_lock_held(self):
        self.analyzer.analyze_lead.side_effect = RuntimeError('API failure')
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'API failure'): self.service.get_battlecard('1')
        self.repo.save_battlecard.assert_not_called()


class ConfigAndErrorTests(unittest.TestCase):
    def test_sql_identifier_validation_and_encoded_password(self):
        with self.assertRaises(ValidationError): Settings(TABLE_LEADS='leads;DROP TABLE leads')
        config = Settings(DB_PASSWORD='a@b:/?#', APP_ENV='development')
        self.assertEqual(config.database_url.password, 'a@b:/?#')

    def test_hosted_mode_requires_strong_auth(self):
        with self.assertRaises(ValidationError): Settings(APP_ENV='production', AUTH_USERNAME='', AUTH_PASSWORD='')
        with self.assertRaises(ValidationError): Settings(APP_ENV='production', AUTH_USERNAME='user', AUTH_PASSWORD='short')

    def test_timezone_normalization(self):
        naive = LeadInteraction(lead_id='1', content='test', created_at=datetime(2026, 1, 1))
        aware = LeadInteraction(lead_id='1', content='test', created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(naive.created_at, aware.created_at)

    def test_provider_failure_messages_distinguish_causes(self):
        req = httpx.Request('POST', 'https://api.openai.com/v1/chat/completions')
        connection = analysis_error_message(APIConnectionError(request=req))
        self.assertIn('cannot connect', connection)
        self.assertNotIn('quota', connection)
        self.assertIn('timed out', analysis_error_message(APITimeoutError(request=req)))
        response = httpx.Response(401, request=req)
        self.assertIn('credentials', analysis_error_message(AuthenticationError('secret', response=response, body=None)))
        quota = RateLimitError('secret', response=httpx.Response(429, request=req), body={'code': 'insufficient_quota'})
        self.assertIn('quota', analysis_error_message(quota))
        self.assertNotIn('secret', analysis_error_message(quota))


if __name__ == '__main__':
    unittest.main()
