# Release Process

## Quick Release

To release a new version of pybundle:

```bash
./release.sh --push-release v2.1.0
```

The script will:
- ✅ Update version in `pyproject.toml`
- ✅ Update version references in `README.md`
- ✅ Commit changes with conventional commit message
- ✅ Create annotated git tag
- ✅ Push to GitHub (triggers PyPI publish via CI)
- ✅ Create GitHub release with auto-generated notes

## Requirements

**Required:**
- Git
- Python 3.9+
- Clean working directory (or confirm to proceed)

**Optional but recommended:**
- GitHub CLI (`gh`) for automatic release creation
  - Install: https://cli.github.com/
  - Authenticate: `gh auth login`

## Version Format

Versions must follow semantic versioning: `vMAJOR.MINOR.PATCH`

Examples:
- `v2.1.0` ✓
- `2.1.0` ✓ (auto-adds `v` prefix)
- `v2.1` ✗ (missing patch)
- `2.1.0-beta` ✗ (pre-release not supported)

## What Gets Updated

### pyproject.toml
```toml
version = "2.1.0"  # Updated automatically
```

### README.md
```markdown
gwc-pybundle==2.1.0  # Updated automatically
```

## Safety Features

The script includes multiple safety checks:

1. **Version validation** - Ensures format is vX.Y.Z
2. **Tag uniqueness** - Prevents duplicate tags
3. **Branch warning** - Warns if not on `main`
4. **Uncommitted changes** - Warns if working directory is dirty
5. **Confirmation prompts** - Asks before destructive operations
6. **Version mismatch detection** - CI validates tag matches pyproject.toml

## CI/CD Integration

When you push a tag (e.g., `v2.1.0`), GitHub Actions automatically:

1. Validates tag matches `pyproject.toml` version
2. Builds source distribution and wheel
3. Publishes to PyPI using trusted publishing

See `.github/workflows/publish.yml` for details.

## Rollback

If something goes wrong:

```bash
# Delete local tag
git tag -d v2.1.0

# Delete remote tag
git push origin :v2.1.0

# Revert version commit
git reset --hard HEAD~1
git push origin main --force
```

## Manual Release (if script fails)

1. Update `pyproject.toml`:
   ```toml
   version = "2.1.0"
   ```

2. Update `README.md`:
   ```markdown
   gwc-pybundle==2.1.0
   ```

3. Commit and tag:
   ```bash
   git add pyproject.toml README.md
   git commit -m "chore: bump version to v2.1.0"
   git tag -a v2.1.0 -m "Release v2.1.0"
   git push origin main
   git push origin v2.1.0
   ```

4. Create GitHub release:
   ```bash
   gh release create v2.1.0 --title "v2.1.0" --generate-notes
   ```

## Testing Releases

To test the release process without publishing to PyPI:

1. Use TestPyPI workflow (`.github/workflows/publish_testpypi.yml`)
2. Create a tag with `-test` suffix: `v2.1.0-test`
3. Or manually build and check:
   ```bash
   python -m build
   ls -la dist/
   ```

## Troubleshooting

### "Tag already exists"
```bash
git tag -d v2.1.0  # Delete local tag
```

### "Version mismatch" in CI
Ensure `pyproject.toml` version matches tag without `v` prefix:
- Tag: `v2.1.0`
- pyproject.toml: `version = "2.1.0"`

### GitHub CLI not authenticated
```bash
gh auth login
```

### PyPI publish fails
Check GitHub Actions logs:
https://github.com/girls-whocode/pybundle/actions

Common issues:
- Version already exists on PyPI (can't overwrite)
- Trusted publisher not configured
- Workflow permissions incorrect

## Version History

- v2.1.0 - Enhanced AI context, smarter dead code detection, confidence-scored dependency analysis
- v2.0.1 - Link validation timeout fixes, signal-to-noise improvements
- v2.0.0 - Roadmap analysis, profile system, 22 advanced steps
