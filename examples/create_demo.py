"""Create a disposable sample course outside the checkout; never overwrite files."""
import argparse
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args();root=args.directory.resolve()
    checkout=Path(__file__).resolve().parents[1]
    if root.is_relative_to(checkout):parser.error('Place sample data outside the checkout')
    if root.exists():parser.error('Choose a new directory; nothing will be overwritten')
    root.mkdir(parents=True)
    (root/'chapter.txt').write_text('第一章：概念与示例。Unicode Ω。\n',encoding='utf8')
    notes=root/'Obsidian笔记';notes.mkdir()
    (notes/'study.md').write_text('# 第一章学习稿\n概念与示例。\n',encoding='utf8')
    print(root)

if __name__=='__main__':main()
