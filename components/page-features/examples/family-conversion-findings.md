# Family-list conversion — content findings

Written by `features.py --convert` (PF-1c (plain-words changes)); each run
rewrites only its own family's section. A content finding names a value
only the list's owner can fix. The converter fixes format only, so every
family list keeps these values exactly as they were: fix them by hand in
the list, then run the converter again to clear the section.

## emails

Source: `platform/views/viewers/_templates/emails.features.json` · 0 content findings

None.

## outlier-demo

Source: `platform/views/viewers/_templates/outlier-demo.features.json` · 8 content findings

- 3: feature 3: source.file is not repo-relative: '/api/settings' starts with /
- 4: feature 4: source.file is not repo-relative: '/api/notify (notify.py)' starts with /
- 23: feature 23: name is 63 characters, over 60
- 34: feature 34: source.file is not repo-relative: '/api/systems' starts with /
- 54: feature 54: source.file is not repo-relative: '/api/card' starts with /
- 57: feature 57: source.file is not repo-relative: '/api/learnings?id=' starts with /
- 61: feature 61: source.file is not repo-relative: '/api/card' starts with /
- 63: feature 63: source.file is not repo-relative: '/api/stops/library, /api/stops/shelf' starts with /

## run-detail

Source: `platform/views/viewers/_templates/run-detail.features.json` · 0 content findings

None.
