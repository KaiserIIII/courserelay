import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
from .store import Store
from .handoff import handoff
from .bundles import audit

def main(argv=None):
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    p=argparse.ArgumentParser(description='CourseRelay 课程资料接续台')
    default=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'CourseRelay'
    p.add_argument('--data-dir',type=Path,default=default)
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('add');a.add_argument('title');a.add_argument('root')
    sub.add_parser('list')
    for name in ('scan','board','handoff'):
        a=sub.add_parser(name);a.add_argument('id',type=int)
    a=sub.add_parser('bundle');a.add_argument('file',type=int);a.add_argument('directory')
    a=sub.add_parser('serve');a.add_argument('--port',type=int,default=8771);a.add_argument('--no-browser',action='store_true')
    args=p.parse_args(argv)
    try:
        data=args.data_dir.resolve()
        if data.is_relative_to(Path(__file__).resolve().parent.parent):raise ValueError('私人数据必须放在源码目录之外')
        s=Store(data/'index.sqlite')
        if args.cmd=='add':value={'id':s.add_course(args.title,args.root)}
        elif args.cmd=='list':value=s.courses()
        elif args.cmd=='scan':value=s.scan(args.id)
        elif args.cmd=='board':value=s.dashboard(args.id)
        elif args.cmd=='handoff':print(handoff(s,args.id));return 0
        elif args.cmd=='bundle':value=audit(s,args.file,args.directory)
        else:
            from .server import serve
            serve(s,args.port,not args.no_browser);return 0
        print(json.dumps(value,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,sqlite3.Error) as ex:
        print('ERROR: '+str(ex),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
