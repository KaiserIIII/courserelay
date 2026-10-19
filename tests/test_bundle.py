import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from courserelay.store import Store
from courserelay.bundles import audit
from courserelay.handoff import handoff, difference


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        b=Path(self.tmp.name).resolve();self.root=b/'course';self.root.mkdir()
        self.s=Store(b/'private/index.sqlite');self.cid=self.s.add_course('中文课 <script>',str(self.root))
        (self.root/'current').mkdir()
        (self.root/'current/a.txt').write_text('new',encoding='utf8')
        (self.root/'current/b.txt').write_text('same',encoding='utf8')
        with ZipFile(self.root/'bundle.zip','w') as z:
            z.writestr('a.txt','old');z.writestr('b.txt','same');z.writestr('missing.txt','x')
        self.s.scan(self.cid)
        self.archive=next(f for f in self.s.dashboard(self.cid)['files'] if f['kind']=='bundle')

    def test_audit_distinguishes_changed_same_and_missing_without_writes(self):
        result=audit(self.s,self.archive['id'],'current')
        self.assertEqual({r['name']:r['status'] for r in result['members']},{'a.txt':'different','b.txt':'same','missing.txt':'missing'})
        self.assertEqual((self.root/'current/a.txt').read_text(),'new')
        self.assertFalse((self.root/'current/missing.txt').exists())

    def test_audit_cannot_escape_course_root(self):
        with self.assertRaises(ValueError):audit(self.s,self.archive['id'],'../private')

    def test_handoff_lists_unmapped_sources_and_does_not_claim_completed(self):
        text=handoff(self.s,self.cid)
        self.assertIn('a.txt',text);self.assertIn('尚无覆盖记录',text)
        self.assertIn('不自动执行',text)

    def test_change_diff_contains_previous_and_current_versions(self):
        p=self.root/'current/a.txt';p.write_text('中文更新',encoding='utf8');self.s.scan(self.cid)
        f=next(f for f in self.s.dashboard(self.cid)['files'] if f['path']==str(p))
        text=difference(f)
        self.assertIn('-new',text);self.assertIn('+中文更新',text)

    def test_handoff_discloses_incomplete_scan(self):
        self.s.scan(self.cid,max_files=1)
        self.assertIn('扫描受限',handoff(self.s,self.cid))
