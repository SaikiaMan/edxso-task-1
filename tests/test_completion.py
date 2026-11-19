import io
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from signalstack.db import rows,put
from signalstack.uploads import ingest
from signalstack.analysis import evidence_excerpts,analyse

class CompletionTests(unittest.TestCase):
    def test_report_targets_use_evidence_in_each_saved_brief(self):
        from signalstack.readiness import readiness
        with TemporaryDirectory() as directory, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(directory)/'test.db')}):
            cid=put('company',0,{'name':'Example'})
            ids=[put('signal',cid,{'kind':'opportunity','support_review':'passed'}) for _ in range(5)]
            put('brief',cid,{'markdown':'Earlier report','signal_ids':ids[:2]})
            self.assertEqual(readiness()['companies'][0]['qualifying_briefs'],0)
            put('brief',cid,{'markdown':'Later report','signal_ids':ids})
            self.assertEqual(readiness()['companies'][0]['qualifying_briefs'],1)

    def test_audit_leaves_unapproved_sources_for_review(self):
        from signalstack.jobs import audit
        with TemporaryDirectory() as directory, patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(directory)/'test.db')}):
            cid=put('company',0,{'name':'Example','website':'https://example.com'})
            put('source',cid,{'url':'https://example.com/candidate','approved':False})
            with patch('signalstack.jobs.fetch_page') as fetch, patch('signalstack.pipeline.reassess',return_value=[]):
                audit(rows('company')[0])
            fetch.assert_not_called()
            report=rows('audit',cid)[0]
            self.assertEqual(report['candidates_for_approval'][0]['url'],'https://example.com/candidate')

    def test_excerpts_are_exact_bounded_source_spans(self):
        text='  '.join('word'+str(i) for i in range(83))
        excerpts=evidence_excerpts(text)
        self.assertEqual(len(excerpts),4)
        for excerpt in excerpts:
            self.assertIn(excerpt,text)
            self.assertLessEqual(len(excerpt.split()),25)

    def test_excel_pdf_and_duplicate_uploads(self):
        from openpyxl import Workbook
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject,NameObject,DictionaryObject
        with TemporaryDirectory(dir=Path.cwd()) as directory,patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(directory)/'test.db')}):
            workbook=Workbook()
            workbook.active.append(['Customer feedback','Need clearer pricing'])
            excel=io.BytesIO();workbook.save(excel);workbook.close()
            id=ingest(1,'feedback.xlsx',excel.getvalue(),synthetic=True)
            self.assertEqual(ingest(1,'feedback.xlsx',excel.getvalue(),synthetic=True),id)
            self.assertIn('Need clearer pricing',rows('record',1)[0]['text'])
            writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
            stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 50 700 Td (Customer requests clear funding guidance.) Tj ET')
            page[NameObject('/Contents')]=writer._add_object(stream)
            pdf=io.BytesIO();writer.write(pdf)
            ingest(1,'feedback.pdf',pdf.getvalue(),synthetic=True)
            self.assertIn('funding guidance',rows('record',1)[0]['text'])
            self.assertEqual(len(rows('record',1)),2)
            self.assertTrue(all(r['synthetic'] for r in rows('record',1)))

    def test_dashboard_create_interview_and_edit(self):
        from streamlit.testing.v1 import AppTest
        with TemporaryDirectory(dir=Path.cwd()) as directory,patch.dict(os.environ,{'SIGNALSTACK_DB':str(Path(directory)/'test.db')}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=20)
            app.text_input[0].set_value('Example')
            app.text_input[1].set_value('https://example.com')
            next(b for b in app.button if b.label=='Create workspace').click().run()
            app.sidebar.selectbox[0].select('1 · Example').run()
            app.sidebar.radio[0].set_value('Company & interview').run()
            self.assertTrue(next(b for b in app.button if b.label=='Show next question').disabled)
            evidence=[{'id':'ev_001','url':'https://example.com','title':'Example','excerpt':'Funding guidance.'}]
            put('research_bundle',1,{'evidence':evidence})
            profile={'products_and_services':{'findings':[],'unknowns':['Service details require confirmation.']}}
            with patch('signalstack.pipeline.profile_from_evidence',return_value={'profile':profile}):
                next(b for b in app.button if b.label=='Research company website and public sources').click().run()
            with patch('signalstack.interview.generate_json',return_value=json.dumps({'topic':'priorities','question':'Which customer problem matters most?'})):
                next(b for b in app.button if b.label=='Show next question').click().run()
            next(t for t in app.text_area if t.label=='Your answer').set_value('Funding uncertainty')
            next(b for b in app.button if b.label=='Save answer').click().run()
            self.assertEqual(rows('interview',1)[0]['session']['turns'][0]['answer'],'Funding uncertainty')
            next(t for t in app.text_area if t.label=='Updated answer').set_value('Application timelines')
            next(b for b in app.button if b.label=='Update answer').click().run()
            self.assertEqual(rows('interview',1)[0]['session']['turns'][0]['answer'],'Application timelines')
            self.assertEqual(len(app.exception),0)
