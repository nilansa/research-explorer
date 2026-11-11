import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('research_taste',Path(__file__).parents[1]/'agent'/'research_taste.py')
rt=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(rt)

class HarnessTests(unittest.TestCase):
    def test_safe_links_and_bounded_retrieval_ranking(self):
        self.assertIsNone(rt.safe_https('file:///secret'))
        self.assertIsNone(rt.safe_https('https://user:pass@example.org/'))
        rows=[{'title':'KV cache compression','abstract':'memory budget','source_url':'https://example.org/a'}, {'title':'Unrelated gardening','abstract':'soil','source_url':'https://example.org/b'}]
        self.assertEqual(rt.bm25('KV cache',rows,1)[0][1]['title'],'KV cache compression')

    def test_prepare_same_evidence_and_distinct_prompts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); evidence=root/'evidence.json'; out=root/'prepared'
            record={'id':'p1','title':'A paper','abstract':'abstract','venue':'V','year':2025,'source_url':'https://example.org/p','provenance':{'service':'mock'}}
            evidence.write_text(json.dumps({'query':'question','records':[record]}))
            rt.cmd_prepare(type('A',(),{'evidence':str(evidence),'outdir':str(out),'seed':7})())
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertTrue(manifest['controls']['same_evidence']);self.assertTrue(manifest['controls']['same_model_required']);self.assertEqual(len(manifest['evidence']),1)
            baseline=(out/'baseline.prompt.txt').read_text();structured=(out/'structured.prompt.txt').read_text()
            self.assertIn('five distinct worthwhile similar RESEARCH PROBLEMS',baseline)
            self.assertIn('one-component swap',structured);self.assertNotEqual(baseline,structured)

    def test_score_has_no_fake_ratings_or_secret_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m=root/'m.json';b=root/'b';s=root/'s';o=root/'out.json'
            m.write_text(json.dumps({'evidence_sha256':'abc'}));b.write_text('proposal https://example.org/a');s.write_text('proposal')
            rt.cmd_score(type('A',(),{'manifest':str(m),'baseline':str(b),'structured':str(s),'out':str(o)})())
            sheet=json.loads(o.read_text())
            self.assertIsNone(sheet['ratings']);self.assertFalse(sheet['scores_fabricated'])
            self.assertTrue(all(x['rating_0_to_4'] is None for x in sheet['rubric']))
            self.assertNotIn('token',json.dumps(sheet).lower());self.assertNotIn('arm_key_private',sheet)

    def test_unavailable_claude_profile_blocks_without_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            manifest=Path(td)/'manifest.json';manifest.write_text(json.dumps({'evidence':[]}))
            with patch.object(rt,'claude_status',return_value=(False,'loggedIn is not true')):
                with self.assertRaises(SystemExit) as ctx:
                    rt.cmd_run(type('A',(),{'manifest':str(manifest),'arm':'baseline','profile':'/tmp/profile','out':str(Path(td)/'private'),'dry_run':False,'model':None})())
                self.assertEqual(ctx.exception.code,2)

    def test_retrieve_accepts_confhub_paper_url(self):
        class FakeResponse:
            status=200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n): return json.dumps({'results':[{
                'id':'paper-01', 'title':'KV cache compression',
                'paper_url':'https://example.org/paper',
                'abstract':'KV cache compression attention output fidelity',
                'venue':'Example', 'year':2025
            }]}).encode('utf-8')
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'evidence.json'
            with patch.object(rt.urllib.request,'urlopen',return_value=FakeResponse()):
                rt.cmd_retrieve(type('Args',(),{'query':'KV cache compression','out':str(output),'limit':6})())
            evidence=json.loads(output.read_text())
            self.assertEqual(len(evidence['records']),1)
            self.assertEqual(evidence['records'][0]['source_url'],'https://example.org/paper')

    def test_blind_sheet_does_not_expose_arm_key(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            man=root/'manifest.json'; a=root/'a.txt';b=root/'b.txt';out=root/'judge.json'
            man.write_text(json.dumps({'evidence_sha256':'abc'}))
            a.write_text('proposal A'); b.write_text('proposal B')
            rt.cmd_score(type('Args',(),{'manifest':str(man),'baseline':str(a),'structured':str(b),'out':str(out)})())
            sheet=json.loads(out.read_text())
            self.assertNotIn('arm_key_private_to_coordinator',sheet)
            self.assertNotIn('blind_id_to_arm',sheet)
            key=json.loads(Path(str(out)+'.mapping.private.json').read_text())
            self.assertEqual(set(key['blind_id_to_arm'].values()),{'baseline','structured'})

if __name__=='__main__': unittest.main()
