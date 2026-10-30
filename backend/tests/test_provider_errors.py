import unittest
from openai import RateLimitError
import httpx2 as httpx
from app.services.analyzer import analysis_error_message
from app.services.provider_errors import provider_error_details


class ProviderErrorsTests(unittest.TestCase):
    def error(self, body, headers=None):
        request = httpx.Request('POST', 'https://api.openai.com/v1/chat/completions')
        return RateLimitError('secret message', response=httpx.Response(429, request=request, headers=headers), body=body)

    def test_specific_billing_codes_take_precedence_over_broad_type(self):
        for code, expected in [('credit_balance_exhausted', 'credits'),
                               ('project_spend_limit_exceeded', 'project spend'),
                               ('organization_spend_limit_exceeded', 'organization spend'),
                               ('organization_usage_limit_exceeded', 'organization usage')]:
            with self.subTest(code=code):
                message = analysis_error_message(self.error({'code': code, 'type': 'insufficient_quota'}))
                self.assertIn(expected, message)
                self.assertNotIn('secret', message)

    def test_nested_and_type_only_quota(self):
        for body in ({'error': {'code': 'insufficient_quota'}}, {'type': 'insufficient_quota'}):
            self.assertIn('quota is exhausted', analysis_error_message(self.error(body)))

    def test_unknown_429_does_not_assume_waiting_will_fix_it(self):
        self.assertIn('billing, quota and model rate limits', analysis_error_message(self.error({})))
        self.assertIn('rate limit reached', analysis_error_message(self.error({'code': 'rate_limit_exceeded'})))

    def test_only_safe_diagnostics_are_returned(self):
        error = self.error({'code': 'slow_down', 'message': 'secret', 'type': 'sk-secret'},
                           {'retry-after': '20', 'authorization': 'secret', 'x-ratelimit-reset-tokens': '1m2s'})
        self.assertEqual(provider_error_details(error), {
            'code': 'slow_down', 'http_status': 429, 'retry-after': '20', 'x-ratelimit-reset-tokens': '1m2s'})
