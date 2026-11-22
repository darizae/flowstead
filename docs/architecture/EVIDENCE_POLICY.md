# Flowstead Evidence Artifact Retention Policy

**Version:** 1.0
**Date:** 2026-11-22

This document defines handling for **new** generated evidence artifacts (screenshots, PDFs, ZIPs, etc.). Previously tracked acceptance evidence remains immutable historical provenance until its case references are deliberately reconciled; this policy does not authorize deleting or rewriting those files.

## 1. Evidence Categories

### Persistent Evidence (Git-tracked)

Small, durable proof artifacts that should remain in the repository:

| Artifact Type | Max Size | Location | Notes |
|--------------|----------|----------|-------|
| JSON coverage reports | 100 KB | `docs/design/evidence/` | CI-ready format |
| Markdown test summaries | 50 KB | `docs/design/evidence/` | Human-readable |
| Small PNG thumbnails | 100 KB | `docs/design/evidence/` | Quick preview |

### Transient Evidence (CI artifacts)

Larger files generated during **new** development or E2E runs:

| Artifact Type | Max Size | Delivery | Notes |
|--------------|----------|----------|-------|
| Full PNG screenshots | 500 KB | GitHub Actions artifact | Browser tests |
| PDF reports | 1 MB | GitHub Actions artifact | Generated reports |
| ZIP archives | 2 MB | GitHub Actions artifact | Test bundles |

## 2. Evidence Location

```
docs/design/evidence/
├── playwright-report/          # Ignored (generated per-run)
├── playwright-test-results/    # Ignored (generated per-run)
├── *.md                        # Persistent summaries
├── *.json                      # Persistent metadata (small)
└── *.png, *.pdf, *.zip         # Transient (upload to CI)
```

## 3. CI Evidence Upload

CI should upload evidence artifacts using GitHub Actions:

```yaml
- name: Upload evidence
  uses: actions/upload-artifact@v4
  with:
    name: evidence-${{ github.sha }}
    path: |
      docs/design/evidence/*.png
      docs/design/evidence/*.pdf
      docs/design/evidence/*.zip
    retention-days: 30
```

## 4. Local Development

- Evidence files generated locally should be small (<100 KB).
- Large artifacts are uploaded to CI and downloaded as needed.
- Playwright reports are gitignored (`docs/design/evidence/playwright-report/`, `docs/design/evidence/playwright-test-results/`).

## 5. Evidence Lifecycle

1. **Generation**: E2E tests produce screenshots/PDFs/ZIPs.
2. **Upload**: CI uploads artifacts to GitHub.
3. **Reference**: Small evidence (JSON, MD) stays in Git.
4. **Cleanup**: CI artifacts expire after 30 days.

## 6. References

- `docs/testing/INDEXED_TEST_PLAN.md` — test catalog
- `docs/testing/TEST_DATA_GUIDE.md` — test data boundaries
- `.gitignore` — ignored evidence directories
