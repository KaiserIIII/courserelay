"""Bounded text projection; never runs Office, macros, fields or formulas."""
import hashlib
import io
from pathlib import Path, PurePosixPath
import re
import stat
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile
from .safe_files import safe_stream, MAX_FILE_BYTES

MAX_MEMBER=8*1024*1024
MAX_EXPANDED=32*1024*1024
MAX_TEXT=200_000

def _members(z):
    infos=z.infolist()
    if len(infos)>2500 or sum(i.file_size for i in infos)>MAX_EXPANDED:
        raise ValueError('Archive exceeds expanded limits')
    names=set()
    for i in infos:
        n=PurePosixPath(i.filename)
        canonical=str(n)+('/' if i.is_dir() else '')
        # Use conservative Windows-compatible names even when auditing on Linux.
        key=str(n).casefold()
        if (key in names or canonical!=i.filename or any(p.endswith(('.', ' ')) for p in n.parts)
            or n.is_absolute() or '..' in n.parts or '\\' in i.filename
            or ':' in i.filename or i.flag_bits&1 or stat.S_ISLNK(i.external_attr>>16)
            or i.file_size>MAX_MEMBER or i.file_size>max(1,i.compress_size)*200):
            raise ValueError('Unsafe or oversized archive member')
        names.add(key)
    return infos

def _xml(data):
    # Removing NULs for this guard also catches UTF-16/32 declarations.
    # ElementTree still validates the original bytes and encoding afterwards.
    declarations=data.replace(b'\0',b'').upper()
    if b'<!DOCTYPE' in declarations or b'<!ENTITY' in declarations:
        raise ValueError('XML declarations are not supported')
    return ET.fromstring(data)

def project(data, suffix):
    if suffix in {'.md','.txt','.sql','.csv','.tsv'}:
        text=data.decode('utf-8-sig')
    elif suffix in {'.docx','.pptx'}:
        with ZipFile(io.BytesIO(data)) as z:
            _members(z)
            if suffix=='.docx':
                root=_xml(z.read('word/document.xml'))
                ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                text='\n'.join(''.join(t.text or '' for t in p.iter(ns+'t')) for p in root.iter(ns+'p'))
            else:
                # Presentation order is relationship order, not slide filename order.
                root=_xml(z.read('ppt/presentation.xml'))
                rr=_xml(z.read('ppt/_rels/presentation.xml.rels'))
                rels={e.attrib['Id']:e.attrib for e in rr}
                if len(rels)!=len(rr):raise ValueError('Duplicate relationship IDs')
                ids=root.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sldId')
                if len(ids)>2500:raise ValueError('Too many slide references')
                targets=[];seen_ids=set();seen_names=set()
                for ix,e in enumerate(ids,1):
                    ident=e.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                    target=rels[ident]
                    raw=target['Target']
                    if target.get('TargetMode')=='External' or '..' in PurePosixPath(raw).parts:
                        raise ValueError('External slide relationship')
                    name=raw.lstrip('/') if raw.startswith('/') else 'ppt/'+raw
                    if ident in seen_ids or name in seen_names:raise ValueError('Repeated slide reference')
                    seen_ids.add(ident);seen_names.add(name);targets.append(name)
                pages=[];length=0
                for ix,name in enumerate(targets,1):
                    slide=_xml(z.read(name))
                    words=[t.text or '' for t in slide.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')]
                    page=(f'[Slide {ix}]\n'+'\n'.join(words))[:MAX_TEXT+1-length]
                    pages.append(page);length+=len(page)+2
                    if length>MAX_TEXT:break
                text='\n\n'.join(pages)
                if len(pages)<len(targets) and len(text)<=MAX_TEXT:text+='\n[PARTIAL]'
    else:
        return '', 'UNKNOWN 此格式仅校验文件版本，未读取正文'
    return text[:MAX_TEXT], ('PARTIAL 正文投影已截断' if len(text)>MAX_TEXT else 'TEXT_ONLY 仅正文文字，不含图片公式及完整排版')

def extract(path, roots):
    try:
        with safe_stream(path, roots) as f:
            data=f.read(MAX_FILE_BYTES+1)
        if len(data)>MAX_FILE_BYTES:raise ValueError('File limit')
        return project(data,Path(path).suffix.casefold())
    except (ValueError,OSError,UnicodeError,KeyError,ET.ParseError,BadZipFile,RuntimeError) as ex:
        return '', 'UNKNOWN '+str(ex)[:160]

def archive_members(path, roots):
    with safe_stream(path,roots) as f:
        data=f.read(MAX_FILE_BYTES+1)
    if len(data)>MAX_FILE_BYTES:raise ValueError('Archive file limit')
    try:
        with ZipFile(io.BytesIO(data)) as z:
            rows=[]
            for i in _members(z):
                if i.is_dir():continue
                if Path(i.filename).suffix.casefold()=='.zip':raise ValueError('Nested ZIP not supported')
                b=z.read(i)
                rows.append({'name':i.filename,'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)})
            return rows
    except BadZipFile as ex:
        raise ValueError('Invalid ZIP') from ex
