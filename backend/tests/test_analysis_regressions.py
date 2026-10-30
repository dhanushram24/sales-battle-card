import json
import unittest
from unittest.mock import Mock, patch

from app.schemas.lead import LeadInteraction
from app.services.analyzer import normalize_score_label
from app.services.summary import EvidenceSummarizer, format_interactions
from tests.test_summary import memory, response
from tests.test_app import output


class AnalysisRegressionTests(unittest.TestCase):
    def summarize_requests(self, items, budget=12000):
        client = Mock()
        client.beta.chat.completions.parse.return_value = response(memory())
        text = format_interactions(items)
        with patch('app.services.summary.CHUNK_MAX_BYTES', budget):
            EvidenceSummarizer(client, 'test').summarize(text)
        requests = [json.loads(call.kwargs['messages'][1]['content'])
                    for call in client.beta.chat.completions.parse.call_args_list]
        self.assertEqual(''.join(request['source_chunk'] for request in requests), text)
        return requests

    def test_long_call_preserves_speaker_and_context(self):
        requests = self.summarize_requests([LeadInteraction(lead_id='1',
            interaction_type='call', direction='outbound',
            content='Customer: ' + 'Still reviewing. ' * 2000 + 'We will not buy.')])
        self.assertGreater(len(requests), 2)
        for request in requests[1:]:
            self.assertIn('channel=call', request['continuation_of'])
            self.assertEqual(request['continuation_speaker_label'], 'Customer:')
            self.assertTrue(request['preceding_source_context'])
        self.assertIn('We will not buy.', requests[-1]['source_chunk'])

    def test_speaker_does_not_leak_from_call_into_unlabelled_email(self):
        requests = self.summarize_requests([
            LeadInteraction(lead_id='1', interaction_type='call', content='Rep: Guaranteed sale!'),
            LeadInteraction(lead_id='1', interaction_type='email', content='Review pending. ' * 2000),
            LeadInteraction(lead_id='1', interaction_type='whatsapp', content='We cancelled.')])
        email_continuations = [r for r in requests if 'channel=email' in r['continuation_of']]
        self.assertTrue(email_continuations)
        self.assertTrue(all(r['continuation_speaker_label'] == 'Unknown' for r in email_continuations))
        self.assertIn('We cancelled.', requests[-1]['source_chunk'])

    def test_split_header_recovers_complete_metadata(self):
        requests = self.summarize_requests([LeadInteraction(lead_id='1',
            interaction_type='call', content='Customer: ' + 'Pending. ' * 50)], budget=32)
        self.assertTrue(any('channel=call' in r['continuation_of'] for r in requests))
        self.assertTrue(all(not r['continuation_of'] or r['continuation_of'].endswith(']') for r in requests))

    def test_numeric_score_determines_classification_without_changing_score(self):
        for score, label in [(0, 'At Risk'), (3.9, 'At Risk'), (4, 'Cold / Stalled'),
                             (6.5, 'Warm'), (8.5, 'Hot'), (10, 'Hot')]:
            result = output().model_copy(update={'overall_score': score,
                'classification': 'Wrong label', 'purchase_outlook': 'undecided'})
            normalize_score_label(result)
            self.assertEqual(result.overall_score, score)
            self.assertEqual(result.classification, label)

    def test_insufficient_evidence_is_not_presented_as_confident(self):
        result = output().model_copy(update={'purchase_outlook': 'insufficient_evidence', 'confidence': 'high'})
        normalize_score_label(result)
        self.assertEqual(result.confidence, 'low')
        self.assertEqual(result.classification, 'Insufficient evidence')


if __name__ == '__main__':
    unittest.main()
