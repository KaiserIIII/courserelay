# Resume

2026-10-19. CourseRelay is a new independent project, not a modification of RelayDesk or the course contents.

Implemented: bounded read-only scan, private SQLite state, version-bound source/output coverage, three chosen output purposes, DOCX/PPTX text projection, previous/current text diff, ZIP member hash comparison, Markdown handoff, Chinese loopback UI and CLI.

Development verification:32 unittest tests passed on local Windows Python3.13.0. Actual personal data and raw validation logs are outside the source checkout. Never commit or publish them.

Independent review's four reproduced issues were fixed with regressions. The browser workflow, including change invalidation and handoff generation, was exercised in a disposable course. Action-time hashes refuse stale coverage/choice records. Clean Windows Python3.13.0 and Linux Python3.14.8 environments each passed32 tests and the disposable CLI flow on implementation e4fea8f. See VALIDATION.md for the precise scope and GitHub for hosted CI status. Initial implementation was f775355.

Important boundary: mappings and current-version choices are explicit records, not proof of semantic coverage or a user's personal acceptance. PDF/images/XLSX have UNKNOWN text semantics. Private bootstrapping records only the reviewed scope, retaining partial/unknown conditions.

Daily use: keep the server terminal open, rescan after adding/editing files, inspect stale mappings, and explicitly record reviewed scopes and chosen-use versions. Stop the app before backing up index.sqlite. Do not add unrelated features after delivery; continue from a concrete user need or reproduced defect.
