# UX Improvements v2.0.2

## User Feedback Summary (January 20, 2026)

After production testing on an enterprise RHEL 8.10 system, we received detailed feedback identifying critical UX issues. The core problem: **"the framework is strong but the report is way noisier than it needs to be for developers."**

## Problems Identified

### 1. Scanning the Universe, Not the Project
- Type coverage showed PyInstaller and `.freeze-venv/` libraries
- Docstring coverage dominated by site-packages
- Config vars listed deps (pip, setuptools, click)
- Secrets detection: "No secrets" then "61,719 high-entropy strings" from `.mypy_cache/`

**Impact**: Developers can't tell *their* problems from *Python's* problems

### 2. FAIL Conditions Lack Developer Meaning
- Overall FAIL due to 2 broken links (documentation issue, not blocker)
- `api-docs` FAIL from pdoc CLI mismatch (version incompatibility)

**Impact**: Status model doesn't reflect actual severity

### 3. Tool Hangs on Enterprise Systems
- `link-validation` hung for 10+ minutes on firewall-blocked external links
- No overall timeout protection
- Sequential checking of unlimited links

**Impact**: Unusable in corporate environments with proxies/firewalls

### 4. Secrets Detection Contradiction
- Says "✓ No obvious secrets detected"
- Then reports "61,719 high-entropy strings"
- No explanation of entropy false positives

**Impact**: Reads like tool is "gaslighting the user"

### 5. Empty Roadmap
- Shows "(none detected)" for entrypoints
- Only searched `src/` for `__main__.py`
- Didn't parse `pyproject.toml` for console scripts

**Impact**: Missed opportunity for project understanding

### 6. Cryptic Error Messages
- `api-docs` failure: "pdoc doesn't recognize --html --fo"
- No version detection or fix suggestions

**Impact**: User has to debug tool failures themselves

## Solutions Implemented

### ✅ Hard Project Scope Boundary (commit 99ecfb9)
**Changes**:
- Added `.freeze-venv`, `site-packages`, `env` to `DEFAULT_EXCLUDE_DIRS`
- Expanded `secrets_detection` to skip all cache/build directories
- Now excludes: venv variants, caches, node_modules, dist, build, target

**Result**: Only scans user's project code by default

### ✅ Link Validation Timeout Protection (commit b57db13)
**Changes**:
- Added 50 link limit (prevents excessive checking)
- Added 2-minute overall timeout
- Reduced per-link timeouts: curl 10s→5s, requests 10s→5s
- Added curl `--connect-timeout 3s` for faster failure detection

**Result**: Completes in <2 minutes even on enterprise systems

### ✅ Secrets Detection Clarity (commit 99ecfb9)
**Changes**:
- "No obvious secrets" → "No pattern-based secrets detected"
- Cap entropy output to top 10 (was 20, often 61k+)
- Added NOTE explaining false positives
- Separate pattern-based (high severity) from entropy-only (low severity)

**Result**: Clear distinction between real findings and noise

### ✅ FAIL/WARN Semantics (commit 99ecfb9)
**Changes**:
- Changed `link-validation` from FAIL to WARN
- Broken links are quality issues, not blockers

**Result**: FAIL now reserved for actual ship-blockers

### ✅ Entrypoint Detection (commit 99ecfb9)
**Changes**:
- Search `root/`, `src/`, and `app/` for `__main__.py` (was only `src/`)
- Parse `pyproject.toml` for PEP 621 `project.scripts`
- Parse `pyproject.toml` for Poetry `tool.poetry.scripts`
- Skip venv/site-packages when detecting

**Result**: Roadmap now finds entrypoints reliably

### ✅ Actionable Error Messages (commit 99ecfb9)
**Changes** (api_docs example):
- Detect and report pdoc version
- Add "💡 How to fix" section for errors
- Explain `--html` vs `--output-dir` version differences
- Use modern pdoc v14+ syntax

**Result**: Self-diagnosing reports

## Impact Metrics

**Before**:
- `link-validation`: Hung 10+ minutes
- `secrets_detection`: 61,719 findings (mostly false positives)
- `roadmap`: "(none detected)"
- `api-docs`: Cryptic failures

**After**:
- `link-validation`: <2 minutes guaranteed
- `secrets_detection`: Top 10 entropy + clear explanation
- `roadmap`: Finds pyproject.toml scripts + __main__.py
- `api-docs`: Version-aware with fix suggestions

## Future Improvements (Suggested, Not Yet Implemented)

### B) Triage Dashboard
- Top 5 issues with severity + file + symbol
- Quick wins (complexity hotspots)
- Risk items (secrets, misconfig)

### E) Fast/Normal/Deep Profiles
- **fast** (<2 min): tree, ruff/mypy, radon, link check, config, secrets patterns
- **normal**: + interrogate, duplication, license scan
- **deep** (nightly): + dependency sizes, git analytics, entropy scan

### F) Better Entrypoint Detection
Add heuristics for:
- `if __name__ == "__main__":` blocks
- FastAPI `app = FastAPI()` patterns
- Uvicorn invocation detection

## Testing Notes

**Test Environment**: RHEL 8.10 (enterprise)
**Project Type**: Unknown (user's company project)
**Issues Encountered**: Link validation hang, scope creep, secrets noise

**Next Steps**:
1. User to test with fixes on RHEL 8.10
2. Monitor for additional feedback
3. Consider implementing fast/normal/deep profiles
4. Add triage dashboard to HANDOFF.md

## Related Commits

- `d3295b3`: Initial link validation timeout fix (duplicate, see b57db13)
- `b57db13`: Link validation timeout protection (tagged v2.0.1)
- `99ecfb9`: Major UX improvements (this document)

## Version Tracking

- **v2.0.0**: Initial release (7 milestones, 22 new steps)
- **v2.0.1**: Link validation timeout fix
- **v2.0.2**: Major UX/signal-to-noise improvements (this release)
