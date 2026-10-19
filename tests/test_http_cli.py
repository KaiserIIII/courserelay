import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from courserelay.store import Store
from courserelay.server import make_server


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        b=Path(self.tmp.name).resolve();self.store=Store(b/'data/index.sqlite')
        root=b/'中文课';root.mkdir();(root/'source.txt').write_text('中文',encoding='utf8')
        self.cid=self.store.add_course('中文课',str(root));self.store.scan(self.cid)
        self.server=make_server(self.store,0,'test-token')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop);self.url=f'http://127.0.0.1:{self.server.server_port}'

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)

    def req(self,path,body=None,token=True,origin=None):
        h={}
        if token:h['Authorization']='Bearer test-token'
        if origin:h['Origin']=origin
        if body is not None:h['Content-Type']='application/json'
        q=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        return urllib.request.urlopen(q,timeout=10)

    def test_unauthenticated_api_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.req('/api/courses',token=False)
        self.assertEqual(c.exception.code,401)
        c.exception.close()

    def test_external_origin_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.req('/api/courses',origin='https://evil.invalid')
        self.assertEqual(c.exception.code,403)
        c.exception.close()

    def test_board_and_handoff_keep_unicode(self):
        with self.req(f'/api/board?id={self.cid}') as r:d=json.load(r)
        self.assertEqual(d['course']['title'],'中文课')
        self.assertNotIn('text',d['files'][0])
        with self.req(f'/api/handoff?id={self.cid}') as r:t=r.read().decode()
        self.assertIn('中文课',t);self.assertIn('source.txt',t)

    def test_invalid_write_cannot_mutate_database(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.req('/api/choose',{'file':-1,'kind':'print'})
        self.assertEqual(c.exception.code,400)
        c.exception.close()
        self.assertEqual(self.store.dashboard(self.cid)['chosen'],[])

    def test_original_download_requires_token_and_current_scanned_bytes(self):
        f=self.store.dashboard(self.cid)['files'][0]
        with self.assertRaises(urllib.error.HTTPError) as c:self.req(f'/api/original?id={f["id"]}',token=False)
        self.assertEqual(c.exception.code,401);c.exception.close()
        with self.req(f'/api/original?id={f["id"]}') as r:
            self.assertEqual(r.read(),'中文'.encode())
            self.assertEqual(r.headers.get_content_type(),'application/octet-stream')
            self.assertIn('attachment;',r.headers['Content-Disposition'])
        Path(f['path']).write_text('externally changed',encoding='utf8')
        with self.assertRaises(urllib.error.HTTPError) as c:self.req(f'/api/original?id={f["id"]}')
        self.assertEqual(c.exception.code,400);c.exception.close()

    def test_cli_can_add_scan_and_export_from_clean_directory(self):
        b=Path(self.tmp.name);data=b/'cli-data'
        def run(*args):return subprocess.run([sys.executable,'-X','utf8','-m','courserelay','--data-dir',str(data),*args],capture_output=True,text=True,encoding='utf8')
        a=run('add','命令行课',self.store.course(self.cid)['root']);self.assertEqual(a.returncode,0,a.stderr)
        cid=json.loads(a.stdout)['id'];s=run('scan',str(cid));self.assertEqual(s.returncode,0,s.stderr)
        h=run('handoff',str(cid));self.assertEqual(h.returncode,0,h.stderr);self.assertIn('命令行课',h.stdout)
        bad=run('scan','9999');self.assertEqual(bad.returncode,1)
