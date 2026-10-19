import difflib
import re

def literal(value):
    text=str(value)
    size=max([len(x) for x in re.findall(r'`+',text)]+[2])+1
    fence='`'*size
    return fence+'\n'+text+'\n'+fence

def difference(file):
    if not file['previous_sha']:return 'UNKNOWN 尚无前一个正文快照；先扫描，再修改，再扫描。'
    if not file['text'] and not file['previous_text']:return 'UNKNOWN 此格式没有可比较正文；仅有哈希变化。'
    return '\n'.join(list(difflib.unified_diff(file['previous_text'].splitlines(),file['text'].splitlines(),fromfile='previous text projection',tofile='current text projection',lineterm=''))[:1500])[:200_000] or '文字投影相同；文件字节仍可能包含排版、图片或属性变化。'

def handoff(store,course_id):
    d=store.dashboard(course_id)
    lines=['# 课程资料更新交接单','','本交接单不自动执行。先读真实来源、教师要求和现有稿件；不把文件存在或本单视作正文已读。','',
           '课程与扫描时间',literal(d['course']['title']+'\n'+str(d['course']['scan_at'])),'',
           '## 尚无覆盖记录或需要重新核对','']
    if d['course']['limited']:
        lines[4:4]=['扫描受限：存在因深度、遍历错误或预算未访问的部分；本单不能证明目录已完整扫描。','']
    for f in d['files']:
        if f['kind']=='source' and f['coverage']!='full':
            lines += [literal(f['path']),f"状态：{f['coverage']}；文件：{f['state']}；{f['format_note']}",'']
    lines += ['## 已记录的关联范围','']
    files={f['id']:f for f in d['files']}
    for e in d['edges']:
        lines += [literal(files[e['source']]['path']+'\n→ '+files[e['output']]['path']+'\n'+e['scope']),f"状态：{e['status']}；记录时间：{e['recorded_at']}",'']
    lines += ['## 当前用途版本','']
    for c in d['chosen']:
        lines += [literal(c['kind']+'\n'+files[c['file']]['path']),f"版本确认：{c['status']}；记录时间：{c['recorded_at']}",'']
    lines += ['## 执行边界','','先保留原件及旧稿。逐份建立来源和页码映射；不能读取的图片、公式与PDF标为UNKNOWN。更新后同时检查学习稿、精简稿、打印稿，再在本工具中重新记录具体字节版本。不要提交平台或公开上传私人课件。','']
    return '\n'.join(lines)
