import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch

from courserelay.formats import extract, archive_members


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()

    def test_docx_keeps_paragraph_order_and_unicode_without_executing_fields(self):
        p=self.root/'notes.docx'
        with ZipFile(p,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>中文001</w:t></w:r></w:p><w:p><w:r><w:instrText>DDE malicious</w:instrText><w:t>第二段</w:t></w:r></w:p></w:document>')
        text,note=extract(str(p),[str(self.root)])
        self.assertEqual(text,'中文001\n第二段');self.assertNotIn('DDE',text)

    def test_unknown_pdf_does_not_claim_content_read(self):
        p=self.root/'scan.pdf';p.write_bytes(b'%PDF-1.4\n')
        text,note=extract(str(p),[str(self.root)])
        self.assertEqual(text,'');self.assertIn('UNKNOWN',note)

    def test_xml_entities_are_rejected(self):
        p=self.root/'bad.docx'
        with ZipFile(p,'w') as z:z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY x "123">]><x>&x;</x>')
        text,note=extract(str(p),[str(self.root)])
        self.assertEqual(text,'');self.assertIn('UNKNOWN',note)

    def test_zip_path_traversal_rejected_without_extracting(self):
        p=self.root/'bad.zip'
        with ZipFile(p,'w') as z:z.writestr('../outside.txt','bad')
        with self.assertRaises(ValueError):archive_members(str(p),[str(self.root)])
        self.assertFalse((self.root.parent/'outside.txt').exists())

    def test_zip_expansion_limit_rejects_bomb(self):
        from zipfile import ZIP_DEFLATED
        p=self.root/'bomb.zip'
        with ZipFile(p,'w',ZIP_DEFLATED) as z:z.writestr('large.txt',b'a'*3_000_000)
        with self.assertRaises(ValueError):archive_members(str(p),[str(self.root)])

    def test_utf16_and_utf32_entities_are_rejected(self):
        for encoding in ('utf-16','utf-16-be','utf-32'):
            with self.subTest(encoding=encoding):
                p=self.root/'encoded.docx'
                xml='<?xml version="1.0"?><!DOCTYPE w:document [<!ENTITY e "expanded_entity">]><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:t>&e;</w:t></w:p></w:document>'
                with ZipFile(p,'w') as z:z.writestr('word/document.xml',xml.encode(encoding))
                text,note=extract(str(p),[str(self.root)])
                self.assertEqual(text,'');self.assertIn('UNKNOWN',note)

    def test_repeated_slide_references_are_rejected_before_amplification(self):
        p=self.root/'repeated.pptx'
        with ZipFile(p,'w') as z:
            z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'+512*'<p:sldId r:id="r1"/>'+'</p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="r1" Target="slides/slide1.xml"/></Relationships>')
            z.writestr('ppt/slides/slide1.xml','<a:t xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'+'x'*65536+'</a:t>')
        original=ZipFile.read;read_bytes=[]
        def tracked(z,*a,**kw):
            data=original(z,*a,**kw);read_bytes.append(len(data));return data
        with patch.object(ZipFile,'read',tracked):text,note=extract(str(p),[str(self.root)])
        self.assertLess(sum(read_bytes),200000)
        self.assertEqual(text,'');self.assertIn('UNKNOWN',note)

    def test_archive_aliases_are_refused_consistently_across_platforms(self):
        for names in (('a.txt','./a.txt'),('a.txt','A.TXT'),('a.txt','a.txt.'),('a.txt','a.txt ')):
            with self.subTest(names=names):
                p=self.root/'aliases.zip'
                with ZipFile(p,'w') as z:
                    for name in names:z.writestr(name,'different')
                with self.assertRaises(ValueError):archive_members(str(p),[str(self.root)])

    def test_valid_slides_stop_at_text_budget_in_presentation_order(self):
        p=self.root/'valid.pptx'
        with ZipFile(p,'w') as z:
            z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'+''.join(f'<p:sldId r:id="r{i}"/>' for i in (3,1,2))+'</p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships>'+''.join(f'<Relationship Id="r{i}" Target="slides/slide{i}.xml"/>' for i in (1,2,3))+'</Relationships>')
            for i in (1,2,3):z.writestr(f'ppt/slides/slide{i}.xml','<a:t xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'+str(i)*100000+'</a:t>')
        original=ZipFile.read;read_names=[]
        def tracked(z,name,*a,**kw):read_names.append(name);return original(z,name,*a,**kw)
        with patch.object(ZipFile,'read',tracked):text,note=extract(str(p),[str(self.root)])
        self.assertEqual(len(text),200000);self.assertIn('PARTIAL',note)
        self.assertTrue(text.startswith('[Slide 1]\n333'));self.assertIn('[Slide 2]\n111',text)
        self.assertNotIn('ppt/slides/slide2.xml',read_names)
