import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from signalstack.db import put,rows
from signalstack.pipeline import discover,research

class PipelineTests(unittest.TestCase):
    def test_discovered_sources_survive_assessment_failure(self):
        with TemporaryDirectory(dir=Path.cwd()) as directory, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(directory)/'test.db')}):
            cid=put('company',0,{'name':'Example','website':'https://example.com','profile':{}})
            plan={'queries':[{'category':'Customers','query':'Example customer problems'}]}
            result={'results':[{'url':'https://example.com/feedback','title':'Feedback','snippet':'Customer problems'}]}
            with patch('signalstack.pipeline.generate_json',side_effect=[json.dumps(plan),RuntimeError('Provider unavailable')]),patch('signalstack.pipeline.search_web',return_value=result):
                self.assertEqual(discover(rows('company')[0]),1)
            self.assertEqual(rows('source',cid)[0]['assessment_status'],'pending')
            self.assertFalse(rows('source',cid)[0]['approved'])
            self.assertEqual(len(rows('discovery_error',cid)),1)

    def test_research_resume_does_not_repeat_search_or_collection(self):
        with TemporaryDirectory(dir=Path.cwd()) as directory, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(directory)/'test.db')}):
            cid=put('company',0,{'name':'Example','website':'https://example.com','profile':{}})
            evidence=[{'id':'ev_001','url':'https://example.com','title':'Example','excerpt':'A company description.'}]
            put('research_bundle',cid,{'evidence':evidence})
            with patch('signalstack.pipeline.plan_searches') as plan,patch('signalstack.pipeline.fetch_page') as fetch,patch('signalstack.pipeline.profile_from_evidence',return_value={'profile':{'example':{}}}):
                research(rows('company')[0])
            plan.assert_not_called()
            fetch.assert_not_called()
            self.assertEqual(rows('company')[0]['profile'],{'example':{}})

    def test_redirect_target_robots_is_checked(self):
        from signalstack.crawler import request
        from unittest.mock import MagicMock
        redirect=MagicMock(is_redirect=True)
        redirect.headers={'Location':'https://example.net/private'}
        with patch('signalstack.crawler.public_url'),patch('signalstack.crawler.requests.get',return_value=redirect) as get,patch('signalstack.crawler.check_robots',side_effect=[None,ValueError('Disallowed')]) as check:
            with self.assertRaisesRegex(ValueError,'Disallowed'): request('https://example.com/start',respect_robots=True)
            self.assertEqual(get.call_count,1)
            self.assertEqual(check.call_args.args[0],'https://example.net/private')
