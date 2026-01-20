# Release Script Examples

## Basic Usage

```bash
# Release version 2.2.0
./release.sh --push-release v2.2.0

# Also works without v prefix (auto-adds it)
./release.sh --push-release 2.2.0
```

## What Happens (Step-by-Step)

### 1. Validation
The script checks:
- ✅ Version format is valid (vX.Y.Z)
- ✅ You're in the repository root
- ✅ Tag doesn't already exist
- ✅ Git working directory state

**Example output:**
```
→ Release version: v2.2.0 (numeric: 2.2.0)
⚠ You have uncommitted changes:
 M pybundle/cli.py
 
Continue anyway? (y/N):
```

### 2. Release Plan
Shows what will happen:
```
═══════════════════════════════════════════════════════════
  Release Plan
═══════════════════════════════════════════════════════════
  Version:     v2.2.0
  Branch:      main
  Will update: pyproject.toml, README.md
  Will create: Git tag v2.2.0
  Will push:   GitHub (triggers PyPI via CI)
  Will create: GitHub Release
═══════════════════════════════════════════════════════════

Proceed with release? (y/N):
```

### 3. Version Updates
Updates files automatically:
```
→ Updating pyproject.toml version to 2.2.0...
✓ Updated pyproject.toml

→ Updating README.md version references...
✓ Updated README.md installation version
```

**What gets changed:**

`pyproject.toml`:
```diff
- version = "2.1.1"
+ version = "2.2.0"
```

`README.md`:
```diff
- gwc-pybundle==2.1.1
+ gwc-pybundle==2.2.0
```

### 4. Commit & Tag
```
→ Committing version changes...
✓ Committed version changes

→ Creating git tag v2.2.0...
✓ Created tag v2.2.0
```

Creates commit: `chore: bump version to v2.2.0`

Creates annotated tag with recent changelog.

### 5. Push Confirmation
```
→ Pushing to GitHub...

⚠ This will push commits and tags, triggering PyPI publish!
Ready to push? (y/N):
```

### 6. Push & Publish
```
✓ Pushed to GitHub (PyPI publish triggered by CI)

→ Waiting 5 seconds for CI to start...

→ Creating GitHub release...
✓ Created GitHub release: https://github.com/girls-whocode/pybundle/releases/tag/v2.2.0
```

### 7. Success Summary
```
═══════════════════════════════════════════════════════════
  Release v2.2.0 Complete!
═══════════════════════════════════════════════════════════

Next steps:
  1. Monitor CI: https://github.com/girls-whocode/pybundle/actions
  2. Verify PyPI: https://pypi.org/project/gwc-pybundle/2.2.0/
  3. Check release: https://github.com/girls-whocode/pybundle/releases/tag/v2.2.0

If anything fails, you can:
  - Delete tag: git tag -d v2.2.0 && git push origin :v2.2.0
  - Revert commit: git reset --hard HEAD~1

✓ Done!
```

## Error Handling

### Invalid Version Format
```bash
$ ./release.sh --push-release 2.2
ERROR: Invalid version format: v2.2 (expected vX.Y.Z, e.g., v2.1.0)
```

### Tag Already Exists
```bash
$ ./release.sh --push-release v2.1.0
ERROR: Tag v2.1.0 already exists. Delete it first if you want to re-release.
```

### Not in Repository Root
```bash
$ cd docs
$ ../release.sh --push-release v2.2.0
ERROR: Must run from repository root (where pyproject.toml exists)
```

## Safety Features

### Uncommitted Changes Warning
```
⚠ You have uncommitted changes:
 M pybundle/cli.py
?? new_file.py

Continue anyway? (y/N):
```

### Wrong Branch Warning
```
⚠ You are on branch 'feature-branch', not 'main'
Continue anyway? (y/N):
```

### Double Confirmation
The script asks for confirmation twice:
1. Before starting the release process
2. Before pushing to GitHub

This prevents accidental releases.

## CI/CD Integration

When you push a tag, GitHub Actions automatically:

1. **Validates version** (NEW!)
   ```bash
   Tag version:      2.2.0
   pyproject.toml:   2.2.0
   ✓ Versions match
   ```

2. **Builds packages**
   ```bash
   python -m build
   ```

3. **Verifies artifacts** (NEW!)
   ```bash
   ✓ dist/ artifacts include version 2.2.0:
     - gwc_pybundle-2.2.0-py3-none-any.whl
     - gwc_pybundle-2.2.0.tar.gz
   ```

4. **Publishes to PyPI**
   ```bash
   ✓ Published to https://pypi.org/project/gwc-pybundle/2.2.0/
   ```

## Rollback Example

If something goes wrong after pushing:

```bash
# 1. Delete the remote tag
git push origin :v2.2.0

# 2. Delete the local tag
git tag -d v2.2.0

# 3. Revert the version commit
git reset --hard HEAD~1

# 4. Force push to restore main
git push origin main --force

# 5. Delete the GitHub release (if created)
gh release delete v2.2.0
```

## Without GitHub CLI

If you don't have `gh` installed:

```
⚠ GitHub CLI (gh) not found. Will skip creating GitHub release.
⚠ Install: https://cli.github.com/

... (rest of release continues normally) ...

✓ Pushed to GitHub (PyPI publish triggered by CI)

Next steps:
  1. Monitor CI: https://github.com/girls-whocode/pybundle/actions
  2. Verify PyPI: https://pypi.org/project/gwc-pybundle/2.2.0/
  
You can create the GitHub release manually at:
https://github.com/girls-whocode/pybundle/releases/new?tag=v2.2.0
```

## Dry Run (Testing)

To see what would happen without actually releasing:

```bash
# The script will ask for confirmation before making changes
./release.sh --push-release v2.2.0

# Answer 'n' to the first confirmation prompt
Proceed with release? (y/N): n
ERROR: Aborted by user
```

Nothing is changed until you confirm.

## Complete Example Output

```bash
$ ./release.sh --push-release v2.2.0

→ Release version: v2.2.0 (numeric: 2.2.0)

═══════════════════════════════════════════════════════════
  Release Plan
═══════════════════════════════════════════════════════════
  Version:     v2.2.0
  Branch:      main
  Will update: pyproject.toml, README.md
  Will create: Git tag v2.2.0
  Will push:   GitHub (triggers PyPI via CI)
  Will create: GitHub Release
═══════════════════════════════════════════════════════════

Proceed with release? (y/N): y

→ Starting release process...
→ Updating pyproject.toml version to 2.2.0...
✓ Updated pyproject.toml
→ Updating README.md version references...
✓ Updated README.md installation version
→ Committing version changes...
[main a1b2c3d] chore: bump version to v2.2.0
 2 files changed, 2 insertions(+), 2 deletions(-)
✓ Committed version changes
→ Creating git tag v2.2.0...
✓ Created tag v2.2.0
→ Pushing to GitHub...

⚠ This will push commits and tags, triggering PyPI publish!
Ready to push? (y/N): y

Enumerating objects: 7, done.
Counting objects: 100% (7/7), done.
Delta compression using up to 8 threads
Compressing objects: 100% (4/4), done.
Writing objects: 100% (4/4), 392 bytes | 392.00 KiB/s, done.
Total 4 (delta 3), reused 0 (delta 0), pack-reused 0
To https://github.com/girls-whocode/pybundle.git
   b23c52b..a1b2c3d  main -> main
 * [new tag]         v2.2.0 -> v2.2.0
✓ Pushed to GitHub (PyPI publish triggered by CI)
→ Waiting 5 seconds for CI to start...
→ Creating GitHub release...
✓ Created GitHub release: https://github.com/girls-whocode/pybundle/releases/tag/v2.2.0

═══════════════════════════════════════════════════════════
  Release v2.2.0 Complete!
═══════════════════════════════════════════════════════════

Next steps:
  1. Monitor CI: https://github.com/girls-whocode/pybundle/actions
  2. Verify PyPI: https://pypi.org/project/gwc-pybundle/2.2.0/
  3. Check release: https://github.com/girls-whocode/pybundle/releases/tag/v2.2.0

If anything fails, you can:
  - Delete tag: git tag -d v2.2.0 && git push origin :v2.2.0
  - Revert commit: git reset --hard HEAD~1

✓ Done!
```

## Tips

1. **Always review changes** before confirming
2. **Monitor CI** after pushing - watch the GitHub Actions workflow
3. **Verify PyPI** within a few minutes to ensure package is available
4. **Keep gh CLI authenticated** for automatic release creation: `gh auth login`
5. **Test on a branch first** if you want to be extra cautious
