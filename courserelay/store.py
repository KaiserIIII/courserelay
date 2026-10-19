"""Private course index. All course files are read-only."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import hashlib
from pathlib import Path
import sqlite3
import threading
from .safe_files import check_file, local_path, safe_stream, MAX_FILE_BYTES
from .formats import extract

OUTPUTS={'full','revision','print'}
ROLES=OUTPUTS|{'source','other','bundle'}
SUFFIXES={'.pdf','.ppt','.pptx','.doc','.docx','.xls','.xlsx','.md','.txt','.png','.jpg','.jpeg','.webp','.sql','.csv','.tsv','.zip'}
SKIP={'node_modules','__pycache__','site-packages','制作记录','核对记录','核对记录 不必打印','仅供自查_不上传','历史版本','复核资料','课程音频','课件PDF'}

def now():return datetime.now(timezone.utc).isoformat()

def guess_role(path):
    if path.suffix.casefold()=='.zip':return 'bundle'
    words='/'.join(path.parts)
    generated=any(x in words for x in ['Obsidian笔记','复习资料','打印资料','CW1','题图复习','提交文件'])
    if generated or any(x in path.name for x in ['One_Page','精简','必背']):
        if path.suffix.casefold() in {'.jpg','.jpeg','.png','.webp'}:return 'other'
        if any(x in path.name for x in ['精简','必背','One_Page','关键词']):return 'revision'
        return 'print' if path.suffix.casefold()=='.pdf' else 'full'
    return 'source'

class Store:
    def __init__(self,path):
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self.db() as c:
            version=c.execute('pragma user_version').fetchone()[0]
            if version not in (0,1):raise ValueError('Unknown index version')
            c.executescript('''
            CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY,title TEXT NOT NULL,root TEXT UNIQUE NOT NULL,scan_at TEXT,limited INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY,course INTEGER NOT NULL,path TEXT NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,sha TEXT,previous_sha TEXT,text TEXT DEFAULT '',previous_text TEXT DEFAULT '',format_note TEXT DEFAULT '',size INTEGER DEFAULT 0,UNIQUE(course,path));
            CREATE TABLE IF NOT EXISTS edges(source INTEGER NOT NULL,output INTEGER NOT NULL,source_sha TEXT NOT NULL,output_sha TEXT NOT NULL,coverage TEXT NOT NULL,scope TEXT NOT NULL,recorded_at TEXT NOT NULL,PRIMARY KEY(source,output));
            CREATE TABLE IF NOT EXISTS chosen(course INTEGER NOT NULL,kind TEXT NOT NULL,file INTEGER NOT NULL,sha TEXT NOT NULL,recorded_at TEXT NOT NULL,PRIMARY KEY(course,kind));
            PRAGMA user_version=1;
            ''')

    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path,timeout=30);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()

    def add_course(self,title,root):
        if not isinstance(title,str) or not 1<=len(title.strip())<=200:raise ValueError('课程名需为1至200字')
        p=local_path(root)
        if not p.is_dir() or p==Path(p.anchor) or self.path.is_relative_to(p):
            raise ValueError('请选择具体课程目录，私人索引必须放在课程目录之外')
        with self.db() as c:
            existing=c.execute('select id from courses where root=?',(str(p),)).fetchone()
            if existing:return existing[0]
            return c.execute('insert into courses(title,root) values(?,?)',(title.strip(),str(p))).lastrowid

    def courses(self):
        with self.db() as c:return [dict(r) for r in c.execute('select * from courses order by title,id')]

    def course(self,cid):
        with self.db() as c:r=c.execute('select * from courses where id=?',(cid,)).fetchone()
        if not r:raise ValueError('课程不存在')
        return dict(r)

    def file(self,fid):
        with self.db() as c:r=c.execute('select * from files where id=?',(fid,)).fetchone()
        if not r:raise ValueError('文件不存在')
        return dict(r)

    def scan(self,cid,max_files=5000,max_bytes=512*1024*1024):
        with self.lock:
            course=self.course(cid);root=Path(course['root'])
            if local_path(str(root))!=root or not root.is_dir():raise ValueError('课程目录缺失或目标发生变化')
            rows=[];limited=False;budget_hit=False;total=0;seen=set()
            def inaccessible(error):
                nonlocal limited
                limited=True
            for base,dirs,names in os.walk(root,followlinks=False,onerror=inaccessible):
                depth=len(Path(base).relative_to(root).parts)
                dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in SKIP and not (Path(base)/d).is_symlink() and not getattr(Path(base)/d,'is_junction',lambda:False)())
                if depth>=12 and dirs:limited=True;dirs[:]=[]
                for name in sorted(names):
                    p=Path(base)/name
                    if p.suffix.casefold() not in SUFFIXES or name.startswith(('~$','.')):continue
                    if len(rows)>=max_files or total>=max_bytes:limited=True;budget_hit=True;break
                    prior=None
                    with self.db() as c:prior=c.execute('select * from files where course=? and path=?',(cid,str(p))).fetchone()
                    result=check_file(str(p),[str(root)],max_bytes=min(MAX_FILE_BYTES,max_bytes-total))
                    total+=result.get('size',0);seen.add(str(p))
                    text,note=(prior['text'],prior['format_note']) if prior else ('','UNKNOWN 未读取正文')
                    if result['state']=='exists' and (not prior or prior['sha']!=result['sha256']):
                        text,note=extract(str(p),[str(root)])
                        repeat=check_file(str(p),[str(root)])
                        if repeat['sha256']!=result['sha256'] or repeat['state']!='exists':
                            result.update(state='changed_during_read',sha256=None)
                            text,note=('','UNKNOWN 读取期间发生变化')
                    rows.append((p,prior,result,text,note))
                if budget_hit:break
            with self.db() as c:
                for p,old,result,text,note in rows:
                    sha=result['sha256'];state=result['state'];size=result.get('size',0)
                    if old:
                        changed=sha is not None and sha!=old['sha']
                        c.execute('update files set state=?,sha=?,previous_sha=?,text=?,previous_text=?,format_note=?,size=? where id=?',
                            (state,sha,old['sha'] if changed else old['previous_sha'],text,old['text'] if changed else old['previous_text'],note,size,old['id']))
                    else:c.execute('insert into files(course,path,kind,state,sha,text,format_note,size) values(?,?,?,?,?,?,?,?)',(cid,str(p),guess_role(p.relative_to(root)),state,sha,text,note,size))
                if not limited:
                    for old in c.execute('select id,path from files where course=?',(cid,)).fetchall():
                        if old['path'] not in seen:
                            result=check_file(old['path'],[str(root)])
                            c.execute('update files set state=? where id=?',('not_scanned' if result['state']=='exists' else result['state'],old['id']))
                c.execute('update courses set scan_at=?,limited=? where id=?',(now(),int(limited),cid))
            return {'files_checked':len(rows),'bytes_checked':total,'limited':limited}

    def set_role(self,fid,kind):
        if kind not in ROLES:raise ValueError('未知文件用途')
        self.file(fid)
        with self.db() as c:c.execute('update files set kind=? where id=?',(kind,fid))

    def fresh(self,f):
        root=self.course(f['course'])['root']
        result=check_file(f['path'],[root])
        if f['state']!='exists' or not f['sha'] or result['state']!='exists' or result['sha256']!=f['sha']:
            raise ValueError('文件已变化或不可读，请重新扫描后核对')

    def original(self,fid):
        f=self.file(fid);root=self.course(f['course'])['root']
        if f['state']!='exists' or not f['sha']:raise ValueError('请先扫描可读文件')
        with safe_stream(f['path'],[root]) as stream:data=stream.read(MAX_FILE_BYTES+1)
        if len(data)>MAX_FILE_BYTES or hashlib.sha256(data).hexdigest()!=f['sha']:
            raise ValueError('文件已变化，请重新扫描后取用')
        return Path(f['path']).name,data

    def cover(self,source,output,coverage,scope):
        if coverage not in {'full','partial'} or not isinstance(scope,str) or not 1<=len(scope.strip())<=2000:
            raise ValueError('请明确完整/部分覆盖和已核对范围')
        with self.lock:
            s=self.file(source);o=self.file(output)
            if s['course']!=o['course'] or s['kind']!='source' or o['kind'] not in OUTPUTS or s['state']!='exists' or o['state']!='exists' or not s['sha'] or not o['sha']:
                raise ValueError('请选择同一课程内已扫描的来源和稿件')
            self.fresh(s);self.fresh(o)
            with self.db() as c:c.execute('insert or replace into edges values(?,?,?,?,?,?,?)',(source,output,s['sha'],o['sha'],coverage,scope.strip(),now()))

    def choose(self,fid,kind):
        if kind not in OUTPUTS:raise ValueError('未知稿件用途')
        with self.lock:
            f=self.file(fid)
            if f['kind'] not in OUTPUTS or f['state']!='exists' or not f['sha']:raise ValueError('只有已扫描的稿件可指定当前版本')
            self.fresh(f)
            with self.db() as c:c.execute('insert or replace into chosen values(?,?,?,?,?)',(f['course'],kind,fid,f['sha'],now()))

    def dashboard(self,cid):
        course=self.course(cid)
        with self.db() as c:
            files=[dict(r) for r in c.execute('select * from files where course=? order by path',(cid,))]
            ids={r['id']:r for r in files}
            edges=[dict(r) for r in c.execute('select e.* from edges e join files f on e.source=f.id where f.course=?',(cid,))]
            chosen=[dict(r) for r in c.execute('select * from chosen where course=?',(cid,))]
        for e in edges:
            s=ids.get(e['source']);o=ids.get(e['output'])
            e['status']='missing' if not s or not o or s['state']!='exists' or o['state']!='exists' else ('stale' if s['sha']!=e['source_sha'] or o['sha']!=e['output_sha'] or s['kind']!='source' or o['kind'] not in OUTPUTS else e['coverage'])
        for f in files:
            refs=[e for e in edges if e['source']==f['id']]
            f['coverage']='full' if any(e['status']=='full' for e in refs) else ('partial' if any(e['status']=='partial' for e in refs) else ('stale' if refs else 'uncovered'))
        for ch in chosen:
            f=ids.get(ch['file'])
            ch['status']='missing' if not f or f['state']!='exists' else ('current' if f['sha']==ch['sha'] and f['kind'] in OUTPUTS else 'stale')
        sources=[f for f in files if f['kind']=='source' and f['state']=='exists']
        counts={k:sum(f['coverage']==k for f in sources) for k in ('uncovered','partial','stale','full')}
        counts['changed']=sum(bool(f['previous_sha']) and f['previous_sha']!=f['sha'] for f in files)
        counts['unavailable']=sum(f['state']!='exists' for f in files)
        return {'course':course,'files':files,'edges':edges,'chosen':chosen,'counts':counts}
