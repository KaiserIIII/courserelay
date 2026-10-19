import tempfile
import unittest
from pathlib import Path
from courserelay.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name).resolve();self.root=base/'课件';self.root.mkdir()
        self.store=Store(base/'private/index.sqlite')
        self.course=self.store.add_course('测试课程',str(self.root))
        self.source=self.root/'chapter.txt';self.source.write_text('原始课件中文',encoding='utf8')
        self.output=self.root/'Obsidian笔记'/'notes.md';self.output.parent.mkdir();self.output.write_text('学习稿',encoding='utf8')

    def files(self):
        return {Path(f['path']).name:f for f in self.store.dashboard(self.course)['files']}

    def test_new_source_remains_uncovered_until_explicit_mapping(self):
        self.store.scan(self.course)
        self.assertEqual(self.store.dashboard(self.course)['counts']['uncovered'],1)
        f=self.files();self.store.cover(f['chapter.txt']['id'],f['notes.md']['id'],'full','全文')
        self.assertEqual(self.store.dashboard(self.course)['counts']['uncovered'],0)

    def test_changed_source_invalidates_only_its_mapping_and_repeated_scan_keeps_diff(self):
        self.store.scan(self.course);f=self.files()
        self.store.cover(f['chapter.txt']['id'],f['notes.md']['id'],'full','全文')
        self.source.write_text('新增第六章',encoding='utf8')
        self.store.scan(self.course);self.store.scan(self.course)
        board=self.store.dashboard(self.course)
        self.assertEqual(board['edges'][0]['status'],'stale')
        changed=next(x for x in board['files'] if x['id']==f['chapter.txt']['id'])
        self.assertEqual(changed['previous_text'],'原始课件中文')

    def test_changed_output_invalidates_chosen_print_and_coverage(self):
        self.store.scan(self.course);f=self.files()
        self.store.choose(f['notes.md']['id'],'print')
        self.store.cover(f['chapter.txt']['id'],f['notes.md']['id'],'full','全文')
        self.output.write_text('有人改过声明',encoding='utf8');self.store.scan(self.course)
        board=self.store.dashboard(self.course)
        self.assertEqual(board['chosen'][0]['status'],'stale')
        self.assertEqual(board['edges'][0]['status'],'stale')

    def test_partial_coverage_remains_in_work_queue(self):
        self.store.scan(self.course);f=self.files()
        self.store.cover(f['chapter.txt']['id'],f['notes.md']['id'],'partial','只处理第1页')
        self.assertEqual(self.store.dashboard(self.course)['counts']['partial'],1)

    def test_missing_source_preserves_history(self):
        self.store.scan(self.course);self.source.unlink();self.store.scan(self.course)
        self.assertEqual(self.files()['chapter.txt']['state'],'missing')
        self.assertEqual(self.files()['chapter.txt']['text'],'原始课件中文')

    def test_limited_scan_does_not_invent_deleted_files(self):
        self.store.scan(self.course)
        self.store.scan(self.course,max_files=1)
        self.assertTrue(self.store.dashboard(self.course)['course']['limited'])
        self.assertTrue(all(f['state']=='exists' for f in self.files().values()))

    def test_cross_course_mapping_is_refused(self):
        self.store.scan(self.course);f=self.files()
        root=self.root.parent/'other';root.mkdir();(root/'a.md').write_text('x')
        other=self.store.add_course('别的课程',str(root));self.store.scan(other)
        fid=self.store.dashboard(other)['files'][0]['id']
        with self.assertRaises(ValueError):self.store.cover(f['chapter.txt']['id'],fid,'full','全文')

    def test_ignore_environment_and_scan_does_not_modify_course_files(self):
        cache=self.root/'.venv'/'lib';cache.mkdir(parents=True);(cache/'fake.txt').write_text('secret')
        before=self.source.read_bytes();self.store.scan(self.course)
        self.assertEqual(len(self.files()),2);self.assertEqual(self.source.read_bytes(),before)

    def test_adoption_requires_output_role(self):
        self.store.scan(self.course);f=self.files()
        with self.assertRaises(ValueError):self.store.choose(f['chapter.txt']['id'],'print')

    def test_depth_pruning_is_disclosed_as_incomplete(self):
        p=self.root
        for _ in range(13):p=p/'deep'
        p.mkdir(parents=True);(p/'hidden.txt').write_text('missed')
        result=self.store.scan(self.course)
        self.assertTrue(result['limited']);self.assertTrue(self.store.course(self.course)['limited'])

    def test_mapping_cannot_accept_changed_files_before_rescan(self):
        self.store.scan(self.course);f=self.files()
        self.source.write_text('changed before click',encoding='utf8')
        with self.assertRaises(ValueError):self.store.cover(f['chapter.txt']['id'],f['notes.md']['id'],'full','全文')
        self.assertEqual(self.store.dashboard(self.course)['edges'],[])

    def test_chosen_version_cannot_accept_changed_output_before_rescan(self):
        self.store.scan(self.course);f=self.files()
        self.output.write_text('changed before click',encoding='utf8')
        with self.assertRaises(ValueError):self.store.choose(f['notes.md']['id'],'print')
        self.assertEqual(self.store.dashboard(self.course)['chosen'],[])
