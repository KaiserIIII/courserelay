"""Loopback-only UI. No course file writes or shell execution."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit,parse_qs,quote
import webbrowser
from .bundles import audit
from .handoff import handoff,difference

ASSETS=Path(__file__).parent/'web'

def ident(v):
    if type(v) is not int or v<=0:raise ValueError('无效编号')
    return v

def make_server(store,port,token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,status=200,ctype='application/json; charset=utf-8',attachment=False,download_name=None):
            body=json.dumps(value,ensure_ascii=False).encode('utf8') if ctype.startswith('application/json') else value.encode('utf8') if isinstance(value,str) else value
            self.send_response(status)
            for k,v in {'Content-Type':ctype,'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"}.items():self.send_header(k,v)
            if attachment:self.send_header('Content-Disposition','attachment; filename="course-handoff.md"')
            if download_name:self.send_header('Content-Disposition',"attachment; filename=download; filename*=UTF-8''"+quote(download_name,safe=''))
            self.end_headers();self.wfile.write(body)
        def guard(self,auth=True):
            host=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host')!=host or self.headers.get('Origin') not in (None,'http://'+host):
                self.send({'error':'Host或Origin不允许'},403);return False
            if auth and not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                self.send({'error':'请通过启动窗口中的会话链接打开'},401);return False
            return True
        def do_GET(self):
            url=urlsplit(self.path);route=url.path
            if not self.guard(route.startswith('/api/')):return
            try:
                if route in {'/','/app.js','/style.css'}:
                    name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[route]
                    mime={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[route]
                    return self.send((ASSETS/name).read_bytes(),ctype=mime)
                if route=='/api/courses':return self.send(store.courses())
                cid=ident(int(parse_qs(url.query).get('id',['0'])[0]))
                if route=='/api/board':
                    d=store.dashboard(cid)
                    for f in d['files']:
                        f.pop('text',None);f.pop('previous_text',None)
                    return self.send(d)
                if route=='/api/file':
                    f=store.file(cid);f['diff']=difference(f);return self.send(f)
                if route=='/api/original':
                    name,data=store.original(cid)
                    return self.send(data,ctype='application/octet-stream',download_name=name)
                if route=='/api/handoff':return self.send(handoff(store,cid),ctype='text/markdown; charset=utf-8',attachment=True)
                return self.send({'error':'找不到页面'},404)
            except (ValueError,KeyError,OSError) as ex:self.send({'error':str(ex)},400)
        def do_POST(self):
            if not self.guard():return
            try:
                n=int(self.headers.get('Content-Length','0'))
                if self.headers.get('Transfer-Encoding') or not 0<n<=16384 or self.headers.get_content_type()!='application/json':raise ValueError('请求格式或长度不允许')
                d=json.loads(self.rfile.read(n))
                if not isinstance(d,dict):raise ValueError('需要JSON对象')
                route=urlsplit(self.path).path
                if route=='/api/course':result={'id':store.add_course(d['title'],d['root'])}
                elif route=='/api/scan':result=store.scan(ident(d['id']))
                elif route=='/api/role':store.set_role(ident(d['file']),d['kind']);result={'saved':True}
                elif route=='/api/cover':store.cover(ident(d['source']),ident(d['output']),d['coverage'],d['scope']);result={'saved':True}
                elif route=='/api/choose':store.choose(ident(d['file']),d['kind']);result={'saved':True}
                elif route=='/api/bundle':result=audit(store,ident(d['file']),d['directory'])
                else:return self.send({'error':'未知操作'},404)
                self.send(result)
            except (ValueError,KeyError,TypeError,OSError) as ex:self.send({'error':str(ex)},400)
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def serve(store,port,open_browser=True):
    token=secrets.token_urlsafe(32);server=make_server(store,port,token)
    url=f'http://127.0.0.1:{server.server_port}/#token={token}'
    print(url,flush=True)
    if open_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
