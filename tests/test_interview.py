import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from signalstack.interview import (
    ask_next_question, build_interview_profile, edit_summary, edit_turn,
    generate_next_question, load_session, new_session, save_session, save_turn,
)


PROFILE = {"company_name": "MeetUniversity", "interview_gaps": {
    "questions": ["Which student segments are highest priority?"]}}


class InterviewTests(unittest.TestCase):
    @patch("signalstack.interview.generate_json")
    def test_two_different_answers_sent_for_adaptive_followups(self, generate):
        for answer, topic, question in [
            ("Students hesitate because they're unsure about funding.", "student_funding", "What funding information do students lack?"),
            ("We want to grow our Germany admissions business.", "germany_growth", "Which student segments are you targeting in Germany?"),
        ]:
            generate.return_value = json.dumps({"topic": topic, "question": question})
            history = [{"topic": "priorities", "question": "What is your priority?", "answer": answer, "skipped": False}]
            self.assertEqual(generate_next_question(PROFILE, history)["topic"], topic)
            payload = json.loads(generate.call_args.args[0].split("\n", 1)[1])
            self.assertEqual(payload["previous_turns"][0]["answer"], answer)
            self.assertEqual(payload["questions_remaining_including_this_one"], 9)

    @patch("signalstack.interview.generate_json")
    def test_pending_resume_skip_and_ten_question_limit(self, generate):
        session = new_session(PROFILE)
        for number in range(10):
            generate.return_value = json.dumps({"topic": f"topic_{number}", "question": f"Question {number}?"})
            question = ask_next_question(session)
            self.assertEqual(ask_next_question(session), question)
            self.assertEqual(generate.call_count, number + 1)
            save_turn(session, question, None if number % 2 else "Answer", bool(number % 2))
        self.assertTrue(build_interview_profile(session)["complete"])
        with self.assertRaises(ValueError):
            ask_next_question(session)
        self.assertEqual(generate.call_count, 10)

    @patch("signalstack.interview.generate_json")
    def test_repeat_and_skipped_topic_rejected(self, generate):
        history = [{"topic": "funding", "question": "Funding concern?", "answer": None, "skipped": True}]
        for result in ({"topic": "other", "question": " funding   concern? "},
                       {"topic": "funding", "question": "How much can customers pay?"},
                       {"topic": "other", "question": " "},
                       {"topic": "other", "question": "Question?", "extra": 1}):
            generate.return_value = json.dumps(result)
            with self.assertRaises(ValueError):
                generate_next_question(PROFILE, history)

    @patch("signalstack.interview.generate_json")
    def test_persistence_edits_and_confidential_history(self, generate):
        generate.return_value = '{"topic":"funding","question":"What funding issues arise?"}'
        session = new_session(PROFILE)
        question = ask_next_question(session)
        with TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "session.json"
            save_session(session, path)
            session = load_session(path)
            self.assertEqual(ask_next_question(session), question)
            save_turn(session, question, None, True)
            edit_turn(session, 0, "Students need scholarship information.")
            edit_summary(session, "funding", "Priority: scholarship guidance")
            save_session(session, path)
            restored = load_session(path)
            summary = build_interview_profile(restored)
            self.assertEqual(summary["questions_displayed"], 1)
            self.assertIn("funding", summary["skipped_topics"])
            self.assertEqual(summary["summary_edits"]["funding"], "Priority: scholarship guidance")
            edit_turn(restored, 0, "Updated answer")
            self.assertNotIn("funding", restored["summary_edits"])

    @patch("signalstack.interview.generate_json")
    def test_blank_answers_and_overwriting_completed_turn_rejected(self, generate):
        generate.return_value = '{"topic":"priorities","question":"What matters most?"}'
        session = new_session(PROFILE)
        question = ask_next_question(session)
        with self.assertRaises(ValueError):
            save_turn(session, question, " ")
        save_turn(session, question, "Growth")
        with self.assertRaises(ValueError):
            save_turn(session, question, "Overwrite")


if __name__ == "__main__":
    unittest.main()
