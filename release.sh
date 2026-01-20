#!/usr/bin/env bash
#
# Release automation script for pybundle
#
# Usage:
#   ./release.sh --push-release v2.1.0
#   ./release.sh --push-release 2.1.0  (auto-adds v prefix)
#
# What it does:
#   1. Validates version format
#   2. Updates pyproject.toml version
#   3. Updates README.md version references
#   4. Commits changes with conventional commit message
#   5. Creates annotated git tag
#   6. Pushes to GitHub (triggers PyPI publish via CI)
#   7. Creates GitHub release with auto-generated notes
#
# Requirements:
#   - gh CLI (GitHub CLI) for release creation
#   - git
#   - python3 with tomllib (3.11+) or tomli package

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

confirm() {
    local prompt="$1"
    local response
    read -p "$(echo -e "${YELLOW}${prompt} (y/N): ${NC}")" response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Check if running from repo root
if [[ ! -f "pyproject.toml" ]] || [[ ! -f "README.md" ]]; then
    error "Must run from repository root (where pyproject.toml exists)"
fi

# Parse arguments
VERSION=""
if [[ $# -eq 2 ]] && [[ "$1" == "--push-release" ]]; then
    VERSION="$2"
else
    error "Usage: $0 --push-release vX.Y.Z"
fi

# Normalize version (add v prefix if missing)
if [[ ! "$VERSION" =~ ^v ]]; then
    VERSION="v${VERSION}"
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Invalid version format: $VERSION (expected vX.Y.Z, e.g., v2.1.0)"
fi

# Extract numeric version (without v prefix)
NUMERIC_VERSION="${VERSION#v}"

info "Release version: $VERSION (numeric: $NUMERIC_VERSION)"

# Check for uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
    warn "You have uncommitted changes:"
    git status --short
    echo
    if ! confirm "Continue anyway?"; then
        error "Aborted. Commit or stash changes first."
    fi
fi

# Check we're on main branch
CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    warn "You are on branch '$CURRENT_BRANCH', not 'main'"
    if ! confirm "Continue anyway?"; then
        error "Aborted. Switch to main branch first."
    fi
fi

# Check if tag already exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    error "Tag $VERSION already exists. Delete it first if you want to re-release."
fi

# Check if we have the GitHub CLI for release creation
if ! command -v gh &> /dev/null; then
    warn "GitHub CLI (gh) not found. Will skip creating GitHub release."
    warn "Install: https://cli.github.com/"
    HAS_GH=false
else
    HAS_GH=true
fi

echo
echo "═══════════════════════════════════════════════════════════"
echo "  Release Plan"
echo "═══════════════════════════════════════════════════════════"
echo "  Version:     $VERSION"
echo "  Branch:      $CURRENT_BRANCH"
echo "  Will update: pyproject.toml, README.md"
echo "  Will create: Git tag $VERSION"
echo "  Will push:   GitHub (triggers PyPI via CI)"
if [[ "$HAS_GH" == "true" ]]; then
    echo "  Will create: GitHub Release"
fi
echo "═══════════════════════════════════════════════════════════"
echo

if ! confirm "Proceed with release?"; then
    error "Aborted by user"
fi

echo
info "Starting release process..."

# Step 1: Update pyproject.toml
info "Updating pyproject.toml version to $NUMERIC_VERSION..."
if command -v python3 &> /dev/null; then
    # Use sed for reliable in-place editing
    sed -i.bak "s/^version = \".*\"/version = \"$NUMERIC_VERSION\"/" pyproject.toml
    rm pyproject.toml.bak
    success "Updated pyproject.toml"
else
    error "python3 not found"
fi

# Step 2: Update README.md version references
info "Updating README.md version references..."

# Update the version in the installation example (gwc-pybundle==X.Y.Z)
if grep -q "gwc-pybundle==" README.md; then
    sed -i.bak "s/gwc-pybundle==[0-9]\+\.[0-9]\+\.[0-9]\+/gwc-pybundle==$NUMERIC_VERSION/" README.md
    rm README.md.bak
    success "Updated README.md installation version"
fi

# Step 3: Commit version bump
info "Committing version changes..."
git add pyproject.toml README.md
git commit -m "chore: bump version to $VERSION" || {
    warn "Nothing to commit (version might already be updated)"
}
success "Committed version changes"

# Step 4: Create annotated tag
info "Creating git tag $VERSION..."
git tag -a "$VERSION" -m "Release $VERSION

$(git log $(git describe --tags --abbrev=0 2>/dev/null || echo "")..HEAD --oneline --no-decorate | head -20)
"
success "Created tag $VERSION"

# Step 5: Push to GitHub
info "Pushing to GitHub..."
echo
warn "This will push commits and tags, triggering PyPI publish!"
if ! confirm "Ready to push?"; then
    error "Aborted. Tag created locally but not pushed. Delete with: git tag -d $VERSION"
fi

git push origin "$CURRENT_BRANCH"
git push origin "$VERSION"
success "Pushed to GitHub (PyPI publish triggered by CI)"

# Step 6: Wait for CI to start (give GitHub a moment)
if [[ "$HAS_GH" == "true" ]]; then
    info "Waiting 5 seconds for CI to start..."
    sleep 5
    
    # Step 7: Create GitHub release
    info "Creating GitHub release..."
    
    # Generate release notes using GitHub's auto-generation
    if gh release create "$VERSION" \
        --title "$VERSION" \
        --generate-notes \
        --verify-tag; then
        success "Created GitHub release: https://github.com/girls-whocode/pybundle/releases/tag/$VERSION"
    else
        warn "Failed to create GitHub release. You can create it manually at:"
        warn "https://github.com/girls-whocode/pybundle/releases/new?tag=$VERSION"
    fi
fi

# Final summary
echo
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}  Release $VERSION Complete!${NC}"
echo "═══════════════════════════════════════════════════════════"
echo
echo "Next steps:"
echo "  1. Monitor CI: https://github.com/girls-whocode/pybundle/actions"
echo "  2. Verify PyPI: https://pypi.org/project/gwc-pybundle/$NUMERIC_VERSION/"
if [[ "$HAS_GH" == "true" ]]; then
    echo "  3. Check release: https://github.com/girls-whocode/pybundle/releases/tag/$VERSION"
fi
echo
echo "If anything fails, you can:"
echo "  - Delete tag: git tag -d $VERSION && git push origin :$VERSION"
echo "  - Revert commit: git reset --hard HEAD~1"
echo
success "Done!"
