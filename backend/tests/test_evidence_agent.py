import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.core.config import settings
from app.schemas.lead import LeadInfo, LeadInteraction
from app.schemas.battlecard import BattlecardAnalysis
from app.services.summary import EvidenceMemory, SUMMARY_MAX_BYTES, SUMMARY_MAX_WORDS, SUMMARY_VERSION, validate_memory
from app.services.evidence_agent import EvidencePreparationAgent
from app.services.analyzer import OpenAILeadAnalyzer
from app.services.usage import TokenUsage


def memory():
    return EvidenceMemory(**{field: 'Unknown' for field in EvidenceMemory.model_fields},
    )


def completion(value):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=value))],
                           usage=SimpleNamespace(prompt_tokens=200, completion_tokens=40))


class MemoryStore:
    def __init__(self): self.data = None
    def get_evidence_memory(self, lead_id): return copy.deepcopy(self.data)
    def save_evidence_memory(self, lead_id, data): self.data = copy.deepcopy(data)


def history():
    return [LeadInteraction(id='a', lead_id='1', content='Older product discussion. ' * 700),
            LeadInteraction(id='b', lead_id='1', content='Customer: We need budget approval before buying.')]


class EvidenceAgentTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.beta.chat.completions.parse.return_value = completion(memory())
        self.store = MemoryStore()
        self.agent = EvidencePreparationAgent(self.client, 'test-model', self.store)
        self.items = history()

    def prepare(self, items=None):
        return self.agent.prepare('1', self.items if items is None else items, 240000)

    def test_unchanged_history_uses_zero_summary_calls(self):
        first = self.prepare()
        self.assertEqual(first.mode, 'rebuilt')
        calls = self.client.beta.chat.completions.parse.call_count
        second = self.prepare()
        self.assertEqual(second.mode, 'reused')
        self.assertEqual(second.usage.as_dict(), dict(calls=0, input_tokens=0, output_tokens=0))
        self.assertEqual(second.processed_bytes, 0)
        self.assertEqual(self.client.beta.chat.completions.parse.call_count, calls)

    def test_append_sends_only_new_evidence_with_original_indices(self):
        self.prepare()
        self.client.beta.chat.completions.parse.reset_mock()
        new = LeadInteraction(id='c', lead_id='1', content='Customer: We now have approval and will sign Friday.')
        result = self.prepare([*self.items, new])
        self.assertEqual(result.mode, 'incremental')
        self.assertEqual(result.reused_interactions, 2)
        calls = self.client.beta.chat.completions.parse.call_args_list
        self.assertEqual(len(calls), 1)
        payload = json.loads(calls[0].kwargs['messages'][1]['content'])
        self.assertIn('[interaction 3;', payload['source_chunk'])
        self.assertNotIn('Older product discussion.', payload['source_chunk'])
        self.assertIn(new.content, payload['source_chunk'])
        self.assertEqual(json.loads(payload['prior_memory']), memory().model_dump())

    def test_edits_deletions_reordering_and_backfills_rebuild(self):
        self.prepare()
        variants = [
            [self.items[0].model_copy(update={'content': self.items[0].content + ' correction'}), self.items[1]],
            [self.items[0]],
            list(reversed(self.items)),
            [LeadInteraction(id='earlier', lead_id='1', content='Earlier objection'), *self.items],
        ]
        snapshot = copy.deepcopy(self.store.data)
        for items in variants:
            with self.subTest(ids=[item.id for item in items]):
                self.store.data = copy.deepcopy(snapshot)
                result = self.prepare(items)
                self.assertEqual(result.mode, 'rebuilt')
                self.assertEqual(result.reused_interactions, 0)

    def test_changed_model_prompt_and_corrupt_cache_rebuild(self):
        self.prepare()
        snapshot = copy.deepcopy(self.store.data)
        for key, value in [('model', 'different'), ('version', 'old'), ('lead_id', 'another-lead'), ('memory', '{}'), ('interaction_hashes', 'invalid')]:
            with self.subTest(key=key):
                self.store.data = {**snapshot, key: value}
                self.assertEqual(self.prepare().mode, 'rebuilt')

    def test_short_history_skips_summarizer_and_cache(self):
        self.store.get_evidence_memory = Mock(side_effect=AssertionError('Should not read cache'))
        prepared = self.prepare([LeadInteraction(lead_id='1', content='No thanks.')])
        self.assertEqual(prepared.mode, 'direct')
        self.client.beta.chat.completions.parse.assert_not_called()

    def test_failed_summary_does_not_overwrite_previous_snapshot(self):
        self.prepare()
        snapshot = copy.deepcopy(self.store.data)
        self.client.beta.chat.completions.parse.return_value = completion(None)
        with self.assertRaises(RuntimeError):
            self.prepare([*self.items, LeadInteraction(lead_id='1', content='New evidence')])
        self.assertEqual(snapshot, self.store.data)

    def test_usage_covers_all_completed_summary_calls(self):
        prepared = self.prepare()
        count = self.client.beta.chat.completions.parse.call_count
        self.assertGreater(count, 1)
        self.assertEqual(prepared.usage.input_tokens, count * 200)
        self.assertEqual(prepared.usage.output_tokens, count * 40)
        self.assertLessEqual(len(prepared.text.encode()), SUMMARY_MAX_BYTES)
        self.assertLessEqual(sum(len(value.split()) for value in json.loads(prepared.text).values()), SUMMARY_MAX_WORDS)

    def test_memory_write_failure_is_reported_without_inventing_score(self):
        self.store.save_evidence_memory = Mock(side_effect=RuntimeError('DB unavailable'))
        self.assertFalse(self.prepare().summary_cache_saved)

    def test_oversize_source_is_rejected_before_any_api_call(self):
        with self.assertRaises(ValueError): self.agent.prepare('1', self.items, 100)
        self.client.beta.chat.completions.parse.assert_not_called()

    def test_summary_version_is_present_and_budget_enforced(self):
        self.prepare()
        self.assertEqual(self.store.data['version'], SUMMARY_VERSION)
        oversized = memory().model_dump()
        oversized['needs_and_fit'] = 'important ' * 301
        with self.assertRaises(ValueError): validate_memory(oversized)


class AnalyzerPipelineTests(unittest.TestCase):
    def test_successful_pipeline_reports_measured_usage_and_reuses_memory(self):
        from tests.test_app import output
        store = MemoryStore()
        with patch.object(settings, 'OPENAI_API_KEY', 'test'):
            analyzer = OpenAILeadAnalyzer(summary_store=store)
            analyzer.client = Mock()
            analyzer.client.beta.chat.completions.parse.side_effect = lambda **kwargs: completion(
                memory() if kwargs['response_format'] is EvidenceMemory else output())
            first = analyzer.analyze_lead(LeadInfo(id='1'), history())
            self.assertEqual(first.analysis_metrics.summary_mode, 'rebuilt')
            self.assertGreater(first.analysis_metrics.summary_usage.calls, 1)
            self.assertEqual(first.analysis_metrics.scoring_usage.input_tokens, 200)
            self.assertEqual(first.overall_score, 0)
            second = analyzer.analyze_lead(LeadInfo(id='1'), history())
            self.assertEqual(second.analysis_metrics.summary_mode, 'reused')
            self.assertEqual(second.analysis_metrics.summary_usage.calls, 0)
            self.assertEqual(second.analysis_metrics.summary_usage.input_tokens, 0)
            self.assertEqual(second.analysis_metrics.scoring_usage.calls, 1)

    def test_compressed_history_drops_unretained_interaction_claims(self):
        from tests.test_app import output
        from app.schemas.battlecard import InteractionSentimentTag
        with patch.object(settings, 'OPENAI_API_KEY', 'test'):
            analyzer = OpenAILeadAnalyzer()
            analyzer.client = Mock()
            analysis = output()
            analysis.interaction_sentiments = [InteractionSentimentTag(interaction_idx=2, score=9,
                label='positive', tone='Ready to buy', key_phrase='We need budget approval before buying.')]
            analyzer.client.beta.chat.completions.parse.side_effect = lambda **kwargs: completion(
                memory() if kwargs['response_format'] is EvidenceMemory else analysis)
            result = analyzer.analyze_lead(LeadInfo(id='1'), history())
            self.assertEqual(result.interaction_sentiments, [])

    def test_failed_scoring_reuses_saved_summary_on_retry(self):
        store = MemoryStore()
        with patch.object(settings, 'OPENAI_API_KEY', 'test'):
            analyzer = OpenAILeadAnalyzer(summary_store=store)
            analyzer.client = Mock()
            summary_calls = []
            def parse(**kwargs):
                if kwargs['response_format'] is EvidenceMemory:
                    summary_calls.append(kwargs)
                    return completion(memory())
                raise RuntimeError('Scoring unavailable')
            analyzer.client.beta.chat.completions.parse.side_effect = parse
            with self.assertRaises(RuntimeError): analyzer.analyze_lead(LeadInfo(id='1'), history())
            count = len(summary_calls)
            self.assertIsNotNone(store.data)
            with self.assertRaises(RuntimeError): analyzer.analyze_lead(LeadInfo(id='1'), history())
            self.assertEqual(len(summary_calls), count)

    def test_metadata_is_not_requested_from_scoring_model(self):
        fields = BattlecardAnalysis.model_fields
        for field in ['analysis_metrics', 'source_utf8_bytes', 'summary_compressed', 'evidence_summary']:
            self.assertNotIn(field, fields)

    def test_unreported_token_usage_is_unknown_not_zero(self):
        usage = TokenUsage()
        usage.record(SimpleNamespace())
        self.assertEqual(usage.calls, 1)
        self.assertIsNone(usage.as_dict()['input_tokens'])


if __name__ == '__main__': unittest.main()
