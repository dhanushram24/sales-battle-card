import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.services.summary import EvidenceMemory, EvidenceSummarizer, split_utf8
from app.services.analyzer import OpenAILeadAnalyzer
from app.schemas.lead import LeadInfo, LeadInteraction


def response(memory):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=memory))])


def memory(value='Unknown'):
    return EvidenceMemory(**{key: value for key in EvidenceMemory.model_fields})


class SummaryTests(unittest.TestCase):
    def test_long_multilingual_input_is_lossless_and_bounded(self):
        text = ('Customer: We cannot buy without approval. नमस्ते 😀\n' * 1500)
        chunks = list(split_utf8(text))
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(len(c.encode('utf-8')) <= 12000 for c in chunks))
        self.assertGreater(len(chunks), 1)

    def test_all_chunks_processed_and_prior_objection_carried(self):
        client = Mock()
        client.beta.chat.completions.parse.return_value = response(memory('Budget rejected'))
        transcript = '[interaction 1; channel=call]\n' + 'discussion ' * 5000 + 'Customer: We will not buy.'
        result = EvidenceSummarizer(client, 'gpt-4o-mini').summarize(transcript)
        calls = client.beta.chat.completions.parse.call_args_list
        self.assertEqual(len(calls), len(list(split_utf8(transcript))))
        self.assertIn('Budget rejected', calls[1].kwargs['messages'][1]['content'])
        self.assertIn('We will not buy.', calls[-1].kwargs['messages'][1]['content'])
        self.assertIn('Budget rejected', result)

    def test_oversize_memory_fails_instead_of_truncating(self):
        client = Mock()
        client.beta.chat.completions.parse.return_value = response(memory('word ' * 1000))
        with self.assertRaises(RuntimeError):
            EvidenceSummarizer(client, 'gpt-4o-mini').summarize('hello')
        self.assertEqual(client.beta.chat.completions.parse.call_count, 2)

    def test_refusal_fails(self):
        client = Mock()
        client.beta.chat.completions.parse.return_value = response(None)
        with self.assertRaises(RuntimeError):
            EvidenceSummarizer(client, 'gpt-4o-mini').summarize('hello')

    @patch('app.services.analyzer.settings')
    def test_long_history_scores_only_summary(self, settings):
        from app.schemas.battlecard import BattlecardAIOutput
        settings.OPENAI_API_KEY = 'test'
        settings.OPENAI_MODEL = 'gpt-4o-mini'
        settings.OPENAI_SUMMARY_MODEL = ''
        settings.MAX_EVIDENCE_BYTES = 240000
        analyzer = OpenAILeadAnalyzer()
        analyzer.client = Mock()
        output = BattlecardAIOutput(
            overall_score=0, classification='At Risk',
            score_breakdown=dict(sentiment_score=5, engagement_score=2, intent_score=0, risk_penalty=4),
            sentiment_summary='Customer rejected purchase.', sentiment_trend='Deteriorating',
            emotional_dimensions=dict(trust_and_rapport=5, commercial_urgency=0, negotiation_stance='Detached'),
            positive_drivers=[dict(quote='Invented promise', channel='call', impact='positive')],
            next_best_action='Confirm rejection.', purchase_outlook='unlikely')
        analyzer.client.beta.chat.completions.parse.return_value = response(output)
        text = 'Product discussion and greetings. ' * 1300 + 'We will not buy.'
        self.assertGreater(len(text.split()), 4000)
        with patch('app.services.summary.EvidenceSummarizer.summarize', return_value=memory('We will not buy.').model_dump_json()) as summarize:
            result = analyzer.analyze_lead(LeadInfo(id='test'), [LeadInteraction(lead_id='test', content=text)])
        self.assertIn('We will not buy.', summarize.call_args.args[0])
        prompt = analyzer.client.beta.chat.completions.parse.call_args.kwargs['messages'][1]['content']
        self.assertNotIn('Product discussion', prompt)
        self.assertTrue(result.summary_compressed)
        self.assertEqual(result.overall_score, 0)
        self.assertEqual(result.positive_drivers, [])
        self.assertLess(result.scoring_evidence_utf8_bytes, result.source_utf8_bytes)

    @patch('app.services.analyzer.settings')
    def test_missing_key_never_generates_demo_score(self, settings):
        settings.OPENAI_API_KEY = ''
        analyzer = OpenAILeadAnalyzer()
        with self.assertRaises(RuntimeError):
            analyzer.analyze_lead(LeadInfo(id='test'), [LeadInteraction(lead_id='test', content='No')])

    @patch('app.services.analyzer.settings')
    def test_empty_evidence_is_not_scored(self, settings):
        settings.OPENAI_API_KEY = 'test'
        analyzer = OpenAILeadAnalyzer()
        with self.assertRaises(ValueError):
            analyzer.analyze_lead(LeadInfo(id='test'), [])


if __name__ == '__main__':
    unittest.main()
