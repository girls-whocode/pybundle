# Debug Profile Improvements v2.0.2

## User Feedback Summary (January 20, 2026)

After testing the **debug** bundle on production RHEL 8.10, feedback confirmed it's "much more developer-helpful" and closer to "what would block me from shipping a clean PR?" The debug profile nails the quick triage loop and keeps scope project-focused.

## What Worked Well

### Quick Triage Loop ✅
- **compileall + ruff check + mypy + pylance** give immediate "is the repo basically sane?" signal
- Collects right supporting context: git status/diff, python version, pip freeze, dependency tree
- Unlike analysis profile, doesn't drown in site-packages noise

### Most Actionable Findings
1. **Radon complexity** - `app/routers/pages.py` function `summary` complexity C (18) - legit refactor callout
2. **Bare exceptions** - `app/upgrade.py` has `except Exception:` blocks - points at failure-hiding risks
3. **Format drift** - 3 files need reformatting (though status was misleading)

## Problems Fixed

### 1. ✅ Formatting Drift Status (MISLEADING → CLEAR)
**Problem**: `ruff format --check` exit=1 marked as **PASS** with note "format drift"
- Confusing: non-zero exit but treated as "fine"
- Devs assume formatting is clean when it isn't

**Fix** ([commit 86d5174](pybundle/steps/ruff.py)):
- Changed to return **WARN** when files need reformatting (exit != 0)
- Note: "exit=1 (format drift detected)"
- Now actionable and clear

### 2. ✅ Command Capture (MISSING → CAPTURED)
**Problem**: HANDOFF.md showed "(not captured)" for command used
- Reproducibility footgun
- "Why did this fail on my machine?" can't be answered

**Fix** ([commit 86d5174](pybundle/cli.py)):
- Capture full `sys.argv` in `cli.main()`
- Store in `ctx.command_used`
- Now shows actual invocation: `pybundle run --profile=debug ...`

### 3. ✅ Tool Status Mismatch (CONFUSING → ACCURATE)
**Problem**: Tools table showed `bandit` and `pip-audit` available, but runs said missing/skipped
- Mismatch confuses developers
- Table should reflect effective availability for this run

**Fix** ([commit 86d5174](pybundle/context.py)):
- Added `bandit` and `pip_audit` fields to `Tooling` dataclass
- Now tracked in `Tooling.detect()` like other tools
- Tools table reflects actual PATH + venv + resolved binary availability

### 4. ✅ Python Version Mismatch (SILENT → LOUD WARNING)
**Problem**: `mypy.ini` specified `python_version = 3.13` but runtime was Python **3.11.14**
- Silently skews type checking
- Can allow newer syntax/stdlib that doesn't exist at runtime
- Or reject valid code that would work

**Fix** ([commit 86d5174](pybundle/steps/mypy.py)):
- Detect mismatch between `mypy.ini` python_version and runtime
- Add **prominent warning** in mypy output header:
  ```
  ⚠ WARNING: Python version mismatch!
    Runtime: Python 3.11
    mypy.ini: python_version = 3.13
    Recommendation: Set mypy.ini python_version = 3.11
  ```
- Also add to step note for quick visibility
- Now developers are alerted to configuration drift

## Known Limitations (Future Work)

### A) Vulture False Positives (Framework Usage)
**Problem**: Vulture flags FastAPI route handlers as unused
- Functions "used" via `@router.*` / `@app.*` decorators, not direct calls
- Classic false-positive pattern
- Becomes "anxiety generator, not cleanup tool"

**Suggested Solutions**:
1. Ship default `vulture_whitelist.py` for common FastAPI patterns
2. Automatically treat `@router.*` / `@app.*` decorated functions as "used"
3. Add Django, Flask, etc. patterns too

**Status**: Not implemented yet, documented for v2.1.0

### B) "No Tests" Should Be Prominent
**Problem**: Pytest/coverage skipped quietly when no tests/ directory exists
- Biggest practical gap for "will this help a dev ship safely?"
- Currently just SKIP status, easy to miss

**Suggested Solution**:
- In HANDOFF.md summary, treat "no tests" as **prominent recommendation**
- Not quiet SKIP, but actionable callout
- "Even 5–10 tests would massively increase value of future runs"

**Status**: Enhancement for future release

### C) Fast/Normal/Deep Profiles
**Problem**: Debug can still be slow for iteration (git-analytics ~4.3 hours, interrogate ~2.6 hours)
- Fine for nightly jobs
- Non-starter for dev iteration loop

**Suggested Approach**:
- **fast** (<2 min): tree, ruff/mypy, radon, link check, config, secrets patterns
- **normal** (current debug): + interrogate, duplication, license scan
- **deep** (nightly): + dependency sizes, git analytics, entropy scan

**Status**: Roadmap item for v2.1.0

## Impact Summary

**Before**: Debug profile was helpful but had trust issues
- Misleading PASS for format drift
- Missing command for reproducibility
- Wrong tool availability info
- Silent Python version skew
- Vulture noise from framework patterns

**After**: Debug profile is "pretty helpful" for pre-PR sanity
- ✅ Clear WARN for actionable items
- ✅ Full reproducibility info
- ✅ Accurate tool detection
- ✅ Loud warnings for config drift
- ⏳ Vulture improvements pending

**User Quote**: "much closer to something I'd actually run before opening a PR"

**Strengths Now**:
- "Is my repo clean?" (lint/type/compile)
- "What should I fix before review?" (format drift, complexity, exceptions)

**Still Weak Where**:
- Can't distinguish framework "usage" (vulture)
- No tests = CI confidence inherently capped

## Testing Notes

**Environment**: RHEL 8.10 (enterprise)
**Project**: FastAPI application with upgrade logic
**Real Findings**: 
- Complexity C(18) in pages.py
- Bare exceptions in upgrade.py
- 3 files need reformatting
- mypy.ini version mismatch (3.13 vs 3.11 runtime)

## Related Commits

- `86d5174`: Debug profile improvements (this document)
- `99ecfb9`: Major UX improvements (analysis profile)
- `b57db13`: Link validation timeout fix

## Version Tracking

- **v2.0.0**: Initial release
- **v2.0.1**: Link validation timeout
- **v2.0.2**: UX + debug improvements (this release)
