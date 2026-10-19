"""Compare an explicit bundle to a same-course directory, without extraction."""
from pathlib import Path, PurePosixPath
from .safe_files import authorized_path, check_file
from .formats import archive_members

def audit(store,archive_id,directory):
    f=store.file(archive_id);c=store.course(f['course']);root=Path(c['root'])
    if f['kind']!='bundle':raise ValueError('请选择ZIP配套包')
    if not isinstance(directory,str) or len(directory)>2000:raise ValueError('Invalid directory')
    rel=PurePosixPath(directory.replace('\\','/'))
    if rel.is_absolute() or '..' in rel.parts or ':' in directory:raise ValueError('只能选择课程内相对目录')
    base=authorized_path(str(root/str(rel)),[str(root)])
    if not base.is_dir():raise ValueError('配套目录不存在')
    before=check_file(f['path'],[str(root)])
    if before['state']!='exists':raise ValueError('ZIP不可读取')
    members=archive_members(f['path'],[str(root)])
    after=check_file(f['path'],[str(root)])
    if before['sha256']!=after['sha256'] or after['state']!='exists':raise ValueError('ZIP读取期间已变化，请重试')
    results=[]
    for m in members:
        target=base/Path(m['name'])
        actual=check_file(str(target),[str(root)])
        status=('same' if actual['sha256']==m['sha256'] else 'different') if actual['state']=='exists' else actual['state']
        results.append(dict(m,path=str(target),current_sha=actual['sha256'],status=status))
    return {'archive':f['path'],'archive_sha':before['sha256'],'directory':str(base),'members':results,'limit':'只对照ZIP成员；没有证明哪版正确或检测目录中全部额外文件'}
