# CourseRelay

A local course-material desk that keeps source files, study notes and the copy you actually use connected.

When another slide deck arrives, CourseRelay shows sources without a recorded mapping, partial coverage and mappings whose file versions have changed. Keep separate choices for full study notes, concise revision notes and print copies. Inspect a previous/current text projection, check a ZIP against its loose files, and export a handoff for the next editing session.

The Chinese interface is intended for personal use. It reads your course files without rewriting them. There is no cloud service, telemetry, model subscription or automatic execution of generated handoffs.

[中文使用指南](README.zh-CN.md) · [Architecture](ARCHITECTURE.md) · [Validation](VALIDATION.md)

## Start

Requires Python3.12+ on Windows or Linux. No pip installation is needed.

```console
python -m courserelay add "Networks" "D:\Courses\Networks"
python -m courserelay scan 1
python -m courserelay serve
```

Windows: run `start.cmd` to open the local desk. Add the directory of one course, then scan it. Linux: use an absolute Linux path and `python3` where necessary.

The default private index is `%LOCALAPPDATA%\CourseRelay` on Windows or `~/.local/share/CourseRelay` on Linux. Choose a directory outside the source checkout and all registered courses to use another location:

```console
python -m courserelay --data-dir "D:\CourseRelayData" serve
```

Keep the terminal open while using the app. Only127.0.0.1 is bound; the launcher URL includes a temporary session token. Keep it private.

## Daily workflow

1. Add a course root you authorize. Scan after downloading or editing materials.
2. Review sources under 待跟进. A missing mapping means no coverage was recorded, not proof you never read it.
3. Use 查看与关联 to correct inferred file roles, choose a source and an output, and describe the pages or questions actually checked. Select partial or full coverage explicitly.
4. Under 现在用哪份, keep separate choices for study, revision and print. Open a selected file's detail and use 下载原文件副本 to download the indexed original bytes. Changed/unreadable files are refused until rescanned. If a linked source or output changes, rescan to invalidate the corresponding snapshot.
5. Export the Markdown handoff. Review it before giving it to an assistant; it does not perform edits itself.

File roles inferred from folder names are suggestions, not verified semantics. The caller may correct them in the UI. Coverage is attached to exact source/output hashes and a written scope; it is not an automated content-completeness judgment.

## ZIP checks and CLI

Select ZIP配套核验, choose an indexed ZIP, and enter a current directory relative to that course root. Members are hashed and compared in place; nothing is extracted or overwritten. Results distinguish same, different, missing and blocked. Extra files outside the archive's member list are not certified.

```console
python -m courserelay list
python -m courserelay board 1
python -m courserelay bundle 42 "assignment/current"
python -m courserelay handoff 1 > handoff.md
python -X utf8 -m unittest discover -s tests -v
```

`42` is an example file ID; obtain actual IDs with `board`. A failed operation exits1. No network accounts are required.

To try a disposable sample, run `python examples/create_demo.py "D:\CourseRelayDemo"` (use a new directory outside the checkout). Add that directory and scan it. Record the source-to-study mapping in the UI, then edit `chapter.txt` and rescan: the earlier mapping becomes stale. The example generator refuses existing directories and does not touch your courses.

## What the tool cannot infer

- A matching hash does not prove a correct answer, full coverage, teacher approval or submission readiness.
- PDF, images, legacy Office and XLSX are version checked with UNKNOWN text semantics. There is no OCR or workbook equivalence checker.
- DOCX/PPTX provide bounded text projections. Images, equations, fields, comments and complete visual layout are not verified; macros and formulas are never executed. Changes outside the projection may produce the same text.
- An initial scan has no previous text snapshot. Future changes are compared to the last different snapshot, not an unlimited version archive.
- Status reflects the last scan, not live monitoring. Mapping and choice actions recheck hashes before saving; other programs may still modify files afterwards. Downloads verify the actual returned bytes.
- Scans exclude caches, audio and several evidence/history folders. Default bounds are5000files,25MiB per file,512MiB cumulative size and12directory levels. Limited results must not be treated as complete scans.
- ZIP checks reject unsafe/noncanonical paths, duplicate or Windows case aliases, encrypted entries, symlinks, generic nested ZIPs and excessive expansion. Conservative naming applies on Linux too. Limits may reject legitimate large documents.
- No hard memory quota or sandbox against another process running as the same OS user. State is private but unencrypted. Stop the app and back up `index.sqlite` before moving it.
- Portability tests and local UI acceptance do not prove classroom learning outcomes or universal file compatibility.

MIT licensed. Reused file-boundary code and its pinned source are documented in [THIRD_PARTY.md](THIRD_PARTY.md). Personal course files, private indexes, screenshots and historical evidence do not belong in the source repository.
