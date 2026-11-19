import json
import io
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from signalstack.discovery import DiscoveryError, TavilyDiscovery, search_web


class SearchWebTests(unittest.TestCase):
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-secret"})
    @patch("signalstack.discovery.urlopen")
    def test_blank_query_makes_zero_requests(self, request):
        with self.assertRaises(ValueError):
            search_web(" \t\n ")
        request.assert_not_called()

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-secret"})
    @patch("signalstack.discovery.urlopen")
    def test_valid_query_makes_one_request(self, request):
        request.return_value = io.StringIO(json.dumps({
            "results": [{"title": "Example", "url": "https://example.com", "content": "Snippet", "score": 0.9}],
            "usage": {"credits": 1},
        }))
        result = search_web("  study abroad  ")
        request.assert_called_once()
        outgoing = request.call_args.args[0]
        self.assertEqual(json.loads(outgoing.data), {
            "query": "study abroad", "search_depth": "basic", "max_results": 5,
            "auto_parameters": False, "include_answer": False,
            "include_raw_content": False, "include_usage": True,
        })
        self.assertEqual(request.call_args.kwargs["timeout"], 30)
        self.assertEqual(outgoing.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(result, {"results": [{"title": "Example", "url": "https://example.com", "snippet": "Snippet"}], "credits_used": 1})

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-secret"})
    @patch("signalstack.discovery.urlopen")
    def test_missing_usage(self, request):
        request.return_value = io.StringIO('{"results": []}')
        self.assertEqual(search_web("example"), {"results": [], "credits_used": None})

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-secret"})
    @patch("signalstack.discovery.urlopen")
    def test_http_failure_is_clear_and_redacted(self, request):
        request.side_effect = HTTPError("https://api.tavily.com/search", 401, "test-secret", {}, None)
        with self.assertRaises(DiscoveryError) as caught:
            search_web("example")
        request.assert_called_once()
        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn("test-secret", str(caught.exception))

    @patch.dict("os.environ", {"TAVILY_API_KEY": ""})
    @patch("signalstack.discovery.urlopen")
    def test_missing_key_makes_zero_requests(self, request):
        with self.assertRaisesRegex(DiscoveryError, "TAVILY_API_KEY is required"):
            search_web("example")
        request.assert_not_called()


class DiscoveryTests(unittest.TestCase):
    def test_search_schema_and_request(self):
        client = TavilyDiscovery(api_key="")
        with patch.object(client, "_request", return_value={
            "answer": "unwanted", "results": [
                {"url": "https://example.com", "title": "Example", "content": "Evidence", "score": 1}
            ]
        }) as request:
            result = client.search("example")
        self.assertEqual(set(result), {"results", "failed_results", "truncated"})
        self.assertEqual(set(result["results"][0]), {"url", "title", "content"})
        self.assertFalse(result["truncated"])
        self.assertFalse(request.call_args.args[1]["include_answer"])

    def test_hard_budget_with_unicode_and_escaped_content(self):
        client = TavilyDiscovery(api_key="", max_output_bytes=512)
        with patch.object(client, "_request", return_value={"results": [
            {"url": "https://example.com", "title": "Example", "content": '\u2603"\\' * 10000}
        ]}):
            result = client.search("example")
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()), 512)

    def test_extract_normalizes_and_preserves_failures(self):
        client = TavilyDiscovery(api_key="")
        with patch.object(client, "_request", return_value={
            "results": [{"url": "https://example.com", "raw_content": "Page"}],
            "failed_results": [{"url": "https://example.org", "error": "Unavailable"}],
        }):
            result = client.extract(["https://example.com", "https://example.org"])
        self.assertEqual(result["results"][0]["content"], "Page")
        self.assertEqual(result["failed_results"][0]["error"], "Unavailable")

    def test_rejects_malformed_results(self):
        client = TavilyDiscovery(api_key="")
        with patch.object(client, "_request", return_value={"results": [{"content": 42}]}):
            with self.assertRaises(DiscoveryError):
                client.search("example")


if __name__ == "__main__":
    unittest.main()
