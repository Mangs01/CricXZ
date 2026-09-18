import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("CACHE_BUCKET", "test-cache")

fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = MagicMock(return_value=MagicMock())
sys.modules.setdefault("boto3", fake_boto3)

import lambda_function


class LambdaTests(unittest.TestCase):
    def test_sanitize_match_keeps_frontend_fields(self):
        match = {
            "id": "abc",
            "name": "India vs Australia",
            "matchType": "odi",
            "status": "India won",
            "teams": ["India", "Australia"],
            "score": [{"r": 250, "w": 7, "o": 50, "inning": "India Inning 1"}],
            "matchStarted": True,
            "matchEnded": True,
            "unwanted": "removed",
        }
        cleaned = lambda_function._sanitize_match(match)
        self.assertEqual(cleaned["teams"], ["India", "Australia"])
        self.assertNotIn("unwanted", cleaned)

    def test_http_request_reads_cache_without_provider_call(self):
        cached = {"status": "success", "data": [{"id": "abc"}]}
        with patch.object(lambda_function, "_read_cache", return_value=cached), patch.object(
            lambda_function, "_fetch_provider"
        ) as provider:
            result = lambda_function.lambda_handler({"requestContext": {}}, None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["data"][0]["id"], "abc")
        provider.assert_not_called()

    def test_schedule_refreshes_cache(self):
        payload = {"status": "success", "data": [{"id": "abc"}]}
        with patch.object(lambda_function, "_fetch_provider", return_value=payload), patch.object(
            lambda_function, "_write_cache"
        ) as write_cache:
            result = lambda_function.lambda_handler({"source": "aws.events"}, None)
        self.assertEqual(result, {"refreshed": True, "matchCount": 1})
        write_cache.assert_called_once_with(payload)


if __name__ == "__main__":
    unittest.main()
