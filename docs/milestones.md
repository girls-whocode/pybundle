# pybundle Development Milestones

Roadmap for expanding pybundle's diagnostic capabilities beyond v1.2.x.

---

## Milestone 1: Quick Wins - Code Quality (v1.3.0) COMPLETED

**Focus:** Low-complexity, high-value static analysis additions

**Priority:** HIGH  
**Complexity:** LOW  
**Target:** Q1 2026

### Features

- **Dead Code Detection** (`vulture`)
  - Identify unused functions, classes, variables
  - Configurable confidence thresholds
  - Integration: `logs/50_vulture.txt`

- **Complexity Metrics** (`radon`)
  - Cyclomatic complexity scoring
  - Maintainability index per module
  - Highlight overly complex functions (>10 complexity)
  - Integration: `logs/51_radon_complexity.txt`

- **Docstring Coverage** (`interrogate`)
  - Percentage of documented functions/classes
  - Missing docstring locations
  - Integration: `logs/52_docstring_coverage.txt`

- **Code Duplication** (`pylint --disable=all --enable=duplicate-code`)
  - Copy-paste detection
  - Configurable similarity threshold
  - Integration: `logs/53_duplication.txt`

### CLI Additions
```bash
--no-vulture / --vulture
--no-radon / --radon
--no-interrogate / --interrogate
```

### Success Criteria
- All 4 tools integrated into `analysis` profile
- Graceful degradation if tools missing
- Doctor mode shows availability
- <100ms overhead per tool

---

## Milestone 2: Dependency Intelligence (v1.3.1) COMPLETED

**Focus:** Advanced dependency analysis and conflict detection

**Priority:** HIGH  
**Complexity:** MEDIUM  
**Target:** Q1 2026

### Features

- **Dependency Tree** (`pipdeptree`)
  - Full dependency graph with conflicts highlighted
  - Circular dependency detection
  - Integration: `meta/30_dependency_tree.txt`

- **Unused Dependencies**
  - Compare `pip freeze` with actual imports (via Pylance)
  - List packages installed but never used
  - Integration: `meta/31_unused_packages.txt`

- **License Scanning** (`pip-licenses`)
  - All package licenses in table format
  - Flag incompatible licenses (GPL + MIT mixing, etc.)
  - Integration: `meta/32_licenses.txt`

- **Dependency Size Analysis**
  - Disk usage per package (via `pip show`)
  - Largest dependencies report
  - Integration: `meta/33_dependency_sizes.txt`

### CLI Additions
```bash
--no-pipdeptree / --pipdeptree
--no-license-scan / --license-scan
--dependency-size-limit N  # Only show top N largest
```

### Success Criteria
- Dependency conflicts surfaced clearly
- Unused package detection accuracy >90%
- License compatibility warnings work for common cases

---

## Milestone 3: Performance Insights (v1.4.0) COMPLETED

**Focus:** Runtime profiling and performance bottleneck detection

**Priority:** MEDIUM  
**Complexity:** HIGH  
**Target:** Q2 2026

### Features

- **CPU Profiling** (`cProfile`)
  - Profile specified entry points or test suite
  - Top 50 slowest functions
  - Integration: `logs/60_cprofile.txt`, `meta/60_cprofile.stats`

- **Import Time Analysis**
  - `python -X importtime` for main module
  - Slowest imports ranked
  - Integration: `logs/61_import_time.txt`

- **Memory Profiling** (`tracemalloc` or `memory_profiler`)
  - Memory snapshots before/after test runs
  - Top memory-consuming functions
  - Integration: `logs/62_memory_profile.txt`

- **Line-by-Line Profiling** (`line_profiler` - optional)
  - Decorator-based hot function profiling
  - Requires manual annotation (via comments or config)
  - Integration: `logs/63_line_profile.txt`

### CLI Additions
```bash
--no-profile / --profile
--profile-entry-point PATH  # e.g., "main.py" or "tests/"
--profile-memory / --no-profile-memory
```

### Success Criteria
- cProfile works on pytest suite by default
- Import time analysis <5s overhead
- Memory profiling doesn't OOM on large projects

---

## Milestone 4: Test Quality & Coverage Enhancement (v1.4.1) - COMPLETED

**Focus:** Beyond line coverage - test effectiveness metrics

**Priority:** MEDIUM  
**Complexity:** MEDIUM  
**Target:** Q2 2026

### Features
- **Give visibility to user of progress**
  - Create an informational colorful output to inform user of pybundle's progress
  - Red if something errors
  - Yellow if something isn't installed
  - Green if step passes

- **Test Flakiness Detection**
  - Run tests 3x, flag non-deterministic failures
  - Track pass/fail patterns
  - Integration: `logs/70_test_flakiness.txt`

- **Branch Coverage Details**
  - Extend coverage.py integration
  - Show missing branches, not just lines
  - Integration: Enhanced `logs/35_coverage.txt`

- **Slow Test Identification**
  - Parse pytest output for >1s tests
  - Rank slowest tests
  - Integration: `logs/71_slow_tests.txt`

- **Mutation Testing** (`mutmut` - optional, expensive)
  - Test code quality by mutating source
  - Shows if tests actually catch bugs
  - Integration: `logs/72_mutation_testing.txt`
  - **NOTE:** Disabled by default (very slow)

### CLI Additions
```bash
--test-flakiness-runs N  # Default: 3
--no-mutation / --mutation  # Mutation testing (slow!)
--slow-test-threshold SECONDS  # Default: 1.0
```

### Success Criteria
- Flakiness detection completes in <3x normal test time
- Branch coverage integrated into existing coverage step
- Mutation testing clearly marked as optional/slow

---

## Milestone 5: Documentation & Type Quality (v1.5.0)

**Focus:** Ensuring documentation completeness and type safety

**Priority:** MEDIUM  
**Complexity:** LOW  
**Target:** Q3 2026

### Features

- **Type Hint Coverage** (custom script)
  - Analyze AST for typed vs untyped functions
  - Percentage metrics + missing locations
  - Integration: `logs/80_type_coverage.txt`

- **README Link Validation** (`markdown-link-check` or custom)
  - Check all URLs in README, CONTRIBUTING, docs/
  - Report broken links
  - Integration: `logs/81_link_validation.txt`

- **API Documentation Generation** (`pdoc` integration)
  - Generate HTML docs into `meta/api_docs/`
  - Check if docstrings parse correctly
  - Integration: `meta/82_api_docs/`

- **Configuration Documentation**
  - Extract all env vars from code (grep + analysis)
  - Document expected config in `meta/83_config_vars.txt`

### CLI Additions
```bash
--no-type-coverage / --type-coverage
--no-link-check / --link-check
--no-api-docs / --api-docs
```

### Success Criteria
- Type coverage aligns with mypy's understanding
- Link checking supports GitHub-flavored markdown
- API docs generate without errors

---

## Milestone 6: Container & Deployment Analysis (v1.5.1)

**Focus:** Docker and containerization best practices

**Priority:** LOW (HIGH for containerized projects)  
**Complexity:** MEDIUM  
**Target:** Q3 2026

### Features

- **Dockerfile Linting** (`hadolint`)
  - Best practice validation
  - Security issue detection
  - Integration: `logs/90_hadolint.txt`

- **Container Image Analysis** (Docker-specific)
  - Layer size breakdown (via `docker history`)
  - Unused layers identification
  - Integration: `meta/90_image_layers.txt`

- **.dockerignore Effectiveness**
  - Compare .dockerignore with actual build context
  - Show what's being copied unnecessarily
  - Integration: `meta/91_dockerignore_analysis.txt`

- **Multi-Stage Build Validation**
  - Ensure intermediate stages don't leak into final image
  - Integration: `logs/91_dockerfile_stages.txt`

### CLI Additions
```bash
--no-dockerfile / --dockerfile
--docker-image NAME  # For image analysis
```

### Success Criteria
- Works when Dockerfile exists, skips gracefully otherwise
- hadolint integration matches existing tool pattern
- Docker image analysis requires docker CLI

---

## Milestone 7: Advanced Git Analytics (v1.6.0)

**Focus:** Deep git history and code ownership insights

**Priority:** LOW  
**Complexity:** MEDIUM  
**Target:** Q4 2026

### Features

- **Blame-Based Analysis**
  - Top contributors by line count
  - Recent churn hotspots (files changed frequently)
  - Integration: `meta/100_git_blame_summary.txt`

- **Branch Health Metrics**
  - Commits ahead/behind main
  - Uncommitted changes summary (enhanced)
  - Integration: Enhanced `meta/00_git_status.txt`

- **Commit Message Quality**
  - Conventional commits validation
  - Average commit message length
  - Integration: `logs/100_commit_quality.txt`

- **Code Ownership Tracking** (`CODEOWNERS` validation)
  - Parse CODEOWNERS file
  - Show coverage of ownership rules
  - Integration: `meta/101_codeowners_coverage.txt`

### CLI Additions
```bash
--no-git-analytics / --git-analytics
--git-blame-depth N  # Commits to analyze (default: 100)
```

### Success Criteria
- Works on any git repo
- Handles large repos (>10k commits) efficiently
- Respects .git-blame-ignore-revs

---

## Milestone 8: Runtime & Dynamic Analysis (v1.6.1)

**Focus:** Understanding code behavior at runtime

**Priority:** MEDIUM  
**Complexity:** HIGH  
**Target:** Q4 2026

### Features

- **Exception Pattern Tracking**
  - Static analysis: find all `raise` statements
  - Categorize exception types used
  - Integration: `logs/110_exception_patterns.txt`

- **Logging Analysis**
  - Extract all logging calls (info, warning, error)
  - Log level distribution
  - Integration: `logs/111_logging_analysis.txt`

- **Function Call Graph** (`pyan` or similar)
  - Static call graph generation
  - Identify orphaned functions
  - Integration: `meta/110_call_graph.dot` (GraphViz)

- **Environment Variable Usage**
  - Grep for `os.getenv`, `os.environ` patterns
  - Document all env vars code expects
  - Integration: `meta/111_env_vars.txt`

### CLI Additions
```bash
--no-runtime-analysis / --runtime-analysis
--call-graph-format {dot,svg,png}
```

### Success Criteria
- Exception tracking finds >95% of raise statements
- Call graph works on projects up to 50k LOC
- Env var detection includes common libraries (click, pydantic)

---

## Milestone 9: Configuration & Security Hardening (v1.7.0)

**Focus:** Advanced security and configuration validation

**Priority:** HIGH (for enterprise)  
**Complexity:** MEDIUM  
**Target:** Q1 2027

### Features

- **Config Schema Validation**
  - Pydantic settings validation
  - .env vs .env.example comparison
  - Integration: `logs/120_config_validation.txt`

- **Enhanced Secrets Detection** (`detect-secrets`)
  - Beyond simple regex patterns
  - Entropy-based detection
  - Integration: `logs/121_secrets_advanced.txt`

- **Environment Completeness**
  - Required vs optional env vars
  - Missing config warnings
  - Integration: `meta/120_config_completeness.txt`

- **Security Headers Analysis** (for web projects)
  - Check if Flask/FastAPI/Django sets security headers
  - Integration: `logs/122_security_headers.txt`

### CLI Additions
```bash
--no-config-validation / --config-validation
--secrets-baseline FILE  # detect-secrets baseline
```

### Success Criteria
- Pydantic integration automatic if detected
- detect-secrets runs without false positives
- Works for non-web projects (skips header check)

---

## Milestone 10: Async & Modern Python (v1.7.1)

**Focus:** AsyncIO and Python 3.9+ features

**Priority:** MEDIUM  
**Complexity:** HIGH  
**Target:** Q1 2027

### Features

- **AsyncIO Task Analysis**
  - Static analysis: find all async def functions
  - Detect missing await calls
  - Integration: `logs/130_async_analysis.txt`

- **Blocking Call Detection**
  - Find sync calls in async functions (requests, time.sleep, etc.)
  - Integration: `logs/131_async_blocking.txt`

- **Event Loop Patterns**
  - Identify event loop creation patterns
  - Check for best practices (asyncio.run vs get_event_loop)
  - Integration: `logs/132_event_loop_patterns.txt`

- **Async Best Practices**
  - Proper exception handling in async
  - TaskGroup usage (3.11+)
  - Integration: Integrated into above logs

### CLI Additions
```bash
--no-async-analysis / --async-analysis
--python-min-version X.Y  # Skip if project uses older Python
```

### Success Criteria
- Works on projects with no async code (skips gracefully)
- Catches common async mistakes (forgotten await, etc.)
- Supports Python 3.7+ async features

---

## Milestone 11: Database & Data Layer (v1.8.0)

**Focus:** Database schema and ORM analysis

**Priority:** LOW (HIGH for DB-heavy projects)  
**Complexity:** HIGH  
**Target:** Q2 2027

### Features

- **Migration History Tracking**
  - Detect Alembic, Django, SQLAlchemy migrations
  - List unapplied migrations
  - Integration: `meta/140_migrations.txt`

- **Schema Documentation**
  - ERD generation from models (via sadisplay or similar)
  - Integration: `meta/140_schema.svg`

- **Query Pattern Analysis**
  - Find potential N+1 queries (static)
  - Identify missing indexes (via model analysis)
  - Integration: `logs/140_query_patterns.txt`

- **ORM Optimization Hints**
  - Suggest select_related/prefetch_related (Django)
  - Lazy loading warnings (SQLAlchemy)
  - Integration: `logs/141_orm_optimization.txt`

### CLI Additions
```bash
--no-db-analysis / --db-analysis
--orm {django,sqlalchemy,tortoise}  # Auto-detect by default
```

### Success Criteria
- Auto-detects ORM from imports
- Migration tracking works for Django + Alembic
- Query analysis limited to static heuristics (no DB connection)

---

## Milestone 12: Framework-Specific Extensions (v1.8.1+)

**Focus:** Deep integration with popular frameworks

**Priority:** LOW (framework-dependent)  
**Complexity:** HIGH  
**Target:** Q2 2027 and beyond

### Features

- **Django System Checks** (`manage.py check --deploy`)
  - Run Django's built-in checks
  - Security, deployment best practices
  - Integration: `logs/150_django_checks.txt`

- **FastAPI Integration**
  - Schema validation (OpenAPI spec generation)
  - Endpoint documentation completeness
  - Integration: `meta/150_openapi.json`

- **Flask Debugging**
  - Debug mode detection in production
  - Secret key validation
  - Integration: `logs/151_flask_checks.txt`

- **SQLAlchemy Validation**
  - Model consistency checks
  - Relationship validation
  - Integration: `logs/152_sqlalchemy_checks.txt`

### CLI Additions
```bash
--framework {auto,django,fastapi,flask,none}
--django-manage PATH  # Default: manage.py
```

### Success Criteria
- Framework auto-detection from imports
- Each framework integration is optional plugin
- Extensible architecture for community frameworks

---

## Implementation Notes
After each milestone is completed, a specific set of commands I would like to run to implement these features.
First, search through all of the code for the previous version It starts with 1.2.1 and replace the following files  with the next version

ARGUMENTS.md
pyproject.toml
README.md
requirements.txt

Then run these commands from the project root:
pip install -e .
git add -A
git commit -m <PLACE COMMIT INFORMATION HERE>
git push
git tag v<VERSION NUMBER>
git push --tags


### Phasing Strategy

**Phase 1 (v1.3.x):** Foundations
- Milestones 1-2 (Code Quality + Dependencies)
- Focus on tools that work everywhere
- Minimal configuration required

**Phase 2 (v1.4.x):** Performance & Testing
- Milestones 3-4 (Performance + Test Quality)
- More expensive operations
- Require explicit enablement

**Phase 3 (v1.5.x-v1.6.x):** Specialization
- Milestones 5-8 (Docs, Containers, Git, Runtime)
- Domain-specific tools
- Opt-in based on project type

**Phase 4 (v1.7.x+):** Advanced & Framework-Specific
- Milestones 9-12 (Security, Async, DB, Frameworks)
- Highly specialized
- Plugin architecture consideration

### Architecture Considerations

1. **Plugin System** (by v1.5.0)
   - Allow third-party step implementations
   - Community-contributed framework integrations

2. **Performance Budget**
   - Each new tool adds <200ms overhead
   - Parallel execution where possible
   - Lazy loading for optional tools

3. **Configuration Model**
   - `pyproject.toml` integration for defaults
   - Profile inheritance and customization
   - Per-project step overrides

4. **Output Organization**
   - Categorize logs: `logs/quality/`, `logs/security/`, `logs/performance/`
   - Unified summary dashboard in SUMMARY.json

### Success Metrics

- **Adoption:** Tool discovery rate (via doctor mode)
- **Actionability:** Findings lead to code changes
- **Performance:** Bundle creation time <2x baseline
- **Stability:** Step failure rate <5%

---

## Community Involvement

### Contribution Opportunities

- **Tool integrations:** Submit new step implementations
- **Framework plugins:** Django, FastAPI, Flask experts
- **Documentation:** Examples, tutorials, best practices
- **Testing:** Run on diverse projects, report issues

### Feedback Channels

- GitHub Issues for feature requests
- Discussions for architecture questions
- Pull requests for implementations

---

**Last Updated:** January 19, 2026  
**Current Version:** 1.2.1  
**Next Release:** 1.3.0 (Target: Q1 2026)
