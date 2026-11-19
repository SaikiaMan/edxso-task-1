import io
import json
import unittest
from unittest.mock import patch

from signalstack.llm import GeminiError, generate_json
from signalstack.research import QUERY_PLAN_SCHEMA, RESEARCH_FIELDS, plan_searches, validate_search_plan
from signalstack.planning_check import run_check


class PlanningTests(unittest.TestCase):
    def test_invalid_plans_make_zero_tavily_calls(self):
        invalid = ['not json', '[]', '{}', '{"queries": ["a"], "extra": 1}',
                   '{"queries": []}', '{"queries": ["a", "b", "c", "d"]}',
                   '{"queries": [" "]}', '{"queries": [1]}',
                   '{"queries": [" A ", "a"]}',
                   '{"queries": ["a"], "queries": ["b"]}']
        for text in invalid:
            with self.subTest(text=text), patch('signalstack.llm.generate_json', return_value=text), patch('signalstack.planning_check.search_web') as search:
                with self.assertRaises(ValueError):
                    run_check()
                search.assert_not_called()

    def test_planner_prompt_and_trimmed_queries(self):
        with patch('signalstack.llm.generate_json', return_value='{"queries": [" official site ", "customer problems"]}') as generate:
            self.assertEqual(plan_searches(' MeetUniversity ', 'https://www.meetuniversity.com'), ['official site', 'customer problems'])
        prompt, schema = generate.call_args.args
        self.assertIn('MeetUniversity', prompt)
        self.assertIn('https://www.meetuniversity.com', prompt)
        for field in RESEARCH_FIELDS:
            self.assertIn(field, prompt)
        self.assertEqual(schema, QUERY_PLAN_SCHEMA)

    def test_invalid_input_does_not_call_gemini(self):
        with patch('signalstack.llm.generate_json') as generate:
            with self.assertRaises(ValueError):
                plan_searches(' ')
            generate.assert_not_called()

    def test_valid_handoff(self):
        with patch('signalstack.llm.generate_json', return_value='{"queries": ["one", "two"]}'), patch('signalstack.planning_check.search_web', return_value={"results": [{"url": "https://example.com"}], "credits_used": 1}) as search, patch('sys.stdout', new_callable=io.StringIO) as output:
            run_check()
        self.assertEqual([call.args[0] for call in search.call_args_list], ['one', 'two'])
        self.assertIn('https://example.com', output.getvalue())
        self.assertIn('credits_used', output.getvalue())

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-secret', 'GEMINI_MODEL_ID': 'test-model'})
    @patch('signalstack.llm.urlopen')
    def test_gemini_request(self, request):
        request.return_value = io.StringIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"queries": ["example"]}'}]}}]}))
        self.assertEqual(validate_search_plan(generate_json('prompt', QUERY_PLAN_SCHEMA)), ['example'])
        request.assert_called_once()
        outgoing = request.call_args.args[0]
        config = json.loads(outgoing.data)['generationConfig']
        self.assertEqual(config['responseMimeType'], 'application/json')
        self.assertEqual(config['responseJsonSchema'], QUERY_PLAN_SCHEMA)
        self.assertEqual(config['maxOutputTokens'], 2048)
        self.assertEqual(request.call_args.kwargs['timeout'], 30)
        self.assertNotIn('test-secret', outgoing.full_url)

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-secret', 'GEMINI_MODEL_ID': 'test-model'})
    @patch('signalstack.llm.urlopen')
    def test_rejects_truncated_generation(self, request):
        request.return_value = io.StringIO(json.dumps({"candidates": [{"finishReason": "MAX_TOKENS"}]}))
        with self.assertRaises(GeminiError):
            generate_json('prompt', QUERY_PLAN_SCHEMA)


if __name__ == '__main__':
    unittest.main()
