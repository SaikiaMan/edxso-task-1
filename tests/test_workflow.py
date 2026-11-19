import json,os,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from signalstack.db import put,rows
from signalstack.jobs import weekly
from signalstack.uploads import ingest

class WorkflowTests(unittest.TestCase):
    def test_scheduler_executes_job(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from threading import Event
        fired=Event()
        scheduler=BackgroundScheduler(timezone='UTC')
        scheduler.add_job(fired.set,'interval',seconds=.1)
        scheduler.start()
        try: self.assertTrue(fired.wait(5))
        finally: scheduler.shutdown()

    def test_failed_analysis_is_visible(self):
        with TemporaryDirectory(dir=Path.cwd()) as folder, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(folder)/'test.db')}):
            cid=put('company',0,{'name':'Failure test','website':'https://example.com'})
            ingest(cid,'feedback.txt',b'Actual customer feedback for testing.')
            with patch('signalstack.analysis.generate_json',side_effect=RuntimeError('Service unavailable')):
                with self.assertRaises(ValueError): weekly(rows('company')[0])
            self.assertEqual(rows('run',cid)[0]['status'],'failed')
            self.assertIn('Service unavailable',str(rows('run',cid)[0]['errors']))
            self.assertEqual(rows('brief',cid),[])

    def test_private_crawl_address_rejected(self):
        from signalstack.crawler import public_url
        with self.assertRaises(ValueError): public_url('http://127.0.0.1/private')

    def test_upload_analysis_brief_and_history(self):
        with TemporaryDirectory(dir=Path.cwd()) as folder, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(folder)/'test.db')}):
            cid=put('company',0,{'name':'Test','website':'https://example.com'})
            company=rows('company')[0]
            ingest(cid,'feedback.csv',b'feedback\nCustomers request clear pricing.\n')
            result={k:'Supported test interpretation' for k in ['development','interpretation','business_area','action','owner','verification']}
            result.update(evidence_index=0,kind='opportunity',verification='source_claim')
            result.update({k:70 for k in ['relevance','impact','urgency','source_reliability','evidence_strength','recency','novelty']})
            with patch('signalstack.analysis.generate_json',return_value=json.dumps(result)),patch('signalstack.review.review_signal',side_effect=lambda c,s:dict(s,support_review='passed')):
                weekly(company)
                weekly(company)
            self.assertEqual(len(rows('signal',cid)),1)
            self.assertEqual(len(rows('brief',cid)),2)
            self.assertEqual(rows('run',cid)[0]['status'],'complete')
            self.assertIn('three-opportunity demonstration target is not yet met',rows('brief',cid)[0]['markdown'])

    def test_crawl_deduplication(self):
        from signalstack.crawler import crawl
        with TemporaryDirectory(dir=Path.cwd()) as folder, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(folder)/'test.db')}):
            page={'url':'https://example.com','title':'Example','text':'Actual page','hash':'same','publication_date':None}
            source={'id':1,'url':page['url'],'category':'Market'}
            with patch('signalstack.crawler.fetch_page',return_value=page):
                self.assertIsNotNone(crawl(1,source))
                self.assertIsNone(crawl(1,source))
            self.assertEqual(len(rows('record',1)),1)
            self.assertEqual(rows('crawl',1)[0]['status'],'unchanged_or_duplicate')

    def test_dashboard_renders(self):
        from streamlit.testing.v1 import AppTest
        with TemporaryDirectory(dir=Path.cwd()) as folder, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(folder)/'test.db')}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=20)
            self.assertEqual(len(app.exception),0)
            put('company',0,{'name':'Test','website':'https://example.com','profile':{}})
            app.run()
            app.sidebar.selectbox[0].select('1 · Test').run()
            for page in ['Overview','Company & interview','Signal Stack','Intelligence','Monday brief','Internal uploads','Settings & runs']:
                app.sidebar.radio[0].set_value(page).run()
                self.assertEqual(len(app.exception),0,page)
