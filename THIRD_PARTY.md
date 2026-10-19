# Reused source

`courserelay/safe_files.py` is copied unchanged from KaiserIIII/relaydesk, commit `e522a3e16cb6e3343b367d6f629ce4507a251ffc`, path `relaydesk/files.py`. Source: https://github.com/KaiserIIII/relaydesk . MIT license, copyright2026 KaiserIIII; license retained in LICENSE. Reused from the already audited local checkout on2026-10-19, not installed or cloned as a Skill.

No third-party runtime packages. Python standard-library components implement the index, local server, archive inspection and Office XML projection. No model/API subscription is used.

CI-only actions reuse the previously audited RelayDesk workflow pins, checked on 2026-10-19: [actions/checkout](https://github.com/actions/checkout) commit `11d5960a326750d5838078e36cf38b85af677262` and [actions/setup-python](https://github.com/actions/setup-python) commit `a26af69be951a213d495a4c3e4e4022e16d87065`. Both are MIT licensed and are not bundled into this application. No Skill installation or recursive dependency installation is performed. Python runtimes are selected by the CI matrix; resolved patch versions are printed per run rather than claimed bit-for-bit reproducible.
