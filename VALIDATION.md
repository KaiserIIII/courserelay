# Validation scope

CourseRelay is a personal local tool, not a research benchmark or a content-correctness checker.

- Development Windows Python 3.13.0: all 32 standard-library tests passed on 2026-10-19, including authenticated HTTP requests and actual CLI subprocesses.
- Independent review: four bounded reproductions (PPTX repeated references, incomplete depth scans, UTF-16 XML entities and ZIP aliases) were fixed. The reviewer reran 31 tests on Windows Python 3.12/3.13 before one additional valid-slide-budget regression was added; no new P1/P2 finding in that reviewed diff.
- Browser acceptance: a disposable course was added and scanned; coverage and chosen-use records were saved; external changes followed by a UI rescan invalidated both, showed a text diff and generated the expected Markdown handoff. Download buttons were exercised; authenticated exact-byte attachment responses were verified separately by HTTP tests. The in-app browser did not expose a saved-download path, so persistence of its download UI is not claimed.
- Real personal course roots were scanned read-only using a private external index. A real assignment ZIP differed from loose Word/PDF files while its spreadsheet matched. Partial question-image coverage retained its declared gaps. These checks validate workflow, not course completeness, answer correctness or submission fitness. Private sources and raw evidence are not included here.

Clean-source acceptance on implementation commit `e4fea8fd2f995d112102c5339d926c103540ef39`:

| Environment | Actual execution | Result |
| --- | --- | --- |
| New local Git clone; new Windows venv; Python 3.13.0 | Full suite with ResourceWarning as error; sample creation; CLI add/scan/board/handoff | 32 tests PASS; CLI PASS |
| Archived commit copied to a new Linux WSL directory; new venv; Python 3.14.8 / GCC 15.2.0 | Same full suite and disposable CLI workflow | 32 tests PASS; CLI PASS |
| Chinese browser UI | Add, scan, map, choose, rescan changed files, inspect diff, handoff preview | PASS within the scope above |

Personal setup:16 course roots,637 indexed records;627 hashable indexed files retained identical hashes across final rescan. This count includes outputs and auxiliary files. Ten records did not have usable hashes under the configured limits; they are not certified unchanged. Excluded/unvisited files are not included in this assurance. Three unrecorded law chapters, one real-estate chapter,20 explicitly partial question sources and the mixed ZIP member results remained visible. These figures describe a private setup, not shipped personal data or a completeness benchmark.

The GitHub Actions workflow is configured for Windows/Linux × Python3.12/3.13 with read-only permissions and pinned actions. Hosted runs must be read from GitHub; configuration alone is not a passing run. CI does not certify real course content or replace browser acceptance.

No exhaustive adversarial filesystem-race proof, hard memory quota, OCR, automatic note generation, live filesystem watching or universal Office compatibility is claimed. One reviewer Windows symlink-replacement probe was NOT RUN because the OS denied symlink creation (WinError 1314). Status and text comparisons have the snapshot/format limits documented in the README.
