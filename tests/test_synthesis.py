import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from signalstack.research import RESEARCH_FIELDS
from signalstack.synthesis import profile_from_evidence, synthesize, validate_evidence


EVIDENCE = [{"id": "ev_001", "url": "https://example.com/about", "title": "About",
             "excerpt": "We offer university counseling."}]


def section(ids=None):
    return {"findings": [{"value": "The company states it offers university counseling.",
                          "status": "verified", "evidence_ids": ids if ids is not None else ["ev_001"]}],
            "unknowns": []}


class SynthesisTests(unittest.TestCase):
    @patch('signalstack.synthesis.generate_json')
    def test_resume_reuses_completed_fields(self, generate):
        fields=list(RESEARCH_FIELDS)
        empty={'findings':[],'unknowns':['Not in supplied evidence.']}
        with TemporaryDirectory(dir=Path.cwd()) as directory:
            generate.side_effect=[json.dumps({fields[0]:empty}),RuntimeError('Temporary failure')]
            with self.assertRaises(RuntimeError):
                profile_from_evidence('Example','https://example.com',EVIDENCE,cache_dir=directory)
            responses=[]
            for field in fields[1:]:
                value=dict(empty)
                if field=='interview_gaps': value['questions']=[]
                responses.append(json.dumps({field:value}))
            generate.reset_mock(side_effect=True)
            generate.side_effect=responses
            result=profile_from_evidence('Example','https://example.com',EVIDENCE,cache_dir=directory)
            self.assertTrue(result['validated'])
            self.assertEqual(generate.call_count,len(fields)-1)

    @patch("signalstack.synthesis.generate_json")
    def test_first_step_uses_only_supplied_evidence(self, generate):
        generate.return_value = json.dumps({"products_and_services": section()})
        result = synthesize(EVIDENCE)
        self.assertEqual(result["products_and_services"]["findings"][0]["evidence_ids"], ["ev_001"])
        prompt, schema = generate.call_args.args
        self.assertIn(EVIDENCE[0]["excerpt"], prompt)
        self.assertEqual(list(schema["properties"]), ["products_and_services"])

    @patch("signalstack.synthesis.generate_json")
    def test_unknown_or_missing_evidence_rejected(self, generate):
        for ids in (["invented"], [], [1], ["ev_001", "ev_001"]):
            generate.return_value = json.dumps({"products_and_services": section(ids)})
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                synthesize(EVIDENCE)

    def test_duplicate_source_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(EVIDENCE * 2)

    @patch("signalstack.synthesis.generate_json")
    def test_graph_resolves_original_metadata_and_preserves_unknowns(self, generate):
        responses = []
        for field in RESEARCH_FIELDS:
            value = section() if field == "products_and_services" else {
                "findings": [], "unknowns": ["Not established by supplied excerpt."]}
            if field == "interview_gaps":
                value["questions"] = ["Who are your highest-value customers?"]
            responses.append(json.dumps({field: value}))
        generate.side_effect = responses
        result = profile_from_evidence("Example", "https://example.com", EVIDENCE)
        self.assertTrue(result["validated"])
        source = result["profile"]["products_and_services"]["findings"][0]["evidence"][0]
        self.assertEqual(source["source_url"], EVIDENCE[0]["url"])
        self.assertEqual(source["excerpt"], EVIDENCE[0]["excerpt"])
        self.assertEqual(generate.call_count, len(RESEARCH_FIELDS))


if __name__ == "__main__":
    unittest.main()
