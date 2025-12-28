# Release Notes Directory

This directory contains detailed release notes for each version of the Alfa by Sinapsi integration.

## Structure

Each release has its own markdown file named with the version number:

- `v0.5.0-beta.1.md` - Beta 1 of version 0.5.0
- `v0.5.0.md` - Stable version 0.5.0
- `v0.6.0.md` - Future version 0.6.0
- etc.

## Viewing Release Notes

### For Users

- **Latest release notes:** Check the [CHANGELOG.md](../../CHANGELOG.md) in the root directory
- **Specific version details:** Browse files in this directory
- **GitHub releases:** Visit the [repository releases page](https://github.com/alexdelprete/ha-sinapsi-alfa/releases)

### For Developers

## Release Documentation Best Practices

### 📋 Two Types of Release Notes

#### 1. **Stable/Official Release Notes** (e.g., v0.5.0)

**These should include ALL changes since the last stable release.**

- **Scope**: Everything from the previous stable release to current
- **Example**: v0.5.0 includes ALL changes since v0.4.2 (the previous stable)
  - All beta changes (beta.1, beta.2, beta.3, etc.)
  - All commits between beta releases
  - All final commits before stable release
- **Purpose**: Give users complete picture of what changed since last stable version they might have installed
- **Typical sections**:
  - What's New Since vX.Y.Z (previous stable)
  - All Critical Bug Fixes
  - All Features Added
  - All Code Quality Improvements
  - All Breaking Changes
  - Complete Dependencies list
  - Comprehensive Migration Notes

#### 2. **Beta Release Notes** (e.g., v0.5.0-beta.1)

**These should document only incremental changes.**

- **Scope**: Only new changes in this specific beta
- **Example**: v0.5.0-beta.2 documents only what changed since beta.1
- **Purpose**: Help beta testers focus on what to test in this iteration
- **Typical sections**:
  - What's New in This Beta
  - Changes Since Previous Beta
  - Specific Bug Fixes in This Beta
  - Testing Focus Areas

### 📝 Practical Example

Let's say you release v0.5.0 with 3 beta versions:

```
v0.4.2 (stable) ← Last stable release
   ↓
v0.5.0-beta.1 → Documents: New feature A, Bug fix B
   ↓
v0.5.0-beta.2 → Documents: New feature C (incremental)
   ↓
v0.5.0-beta.3 → Documents: Bug fix D (incremental)
   ↓
Final commits → UI polish, dependency updates
   ↓
v0.5.0 (stable) → Documents: EVERYTHING (A+B+C+D+polish+deps)
```

**v0.5.0.md should contain**:

- Feature A, B, C, D
- All bug fixes (B, D, and any others)
- All dependency updates
- All polish and improvements
- Complete changelog since v0.4.2

This ensures users upgrading directly from v0.4.2 → v0.5.0 (skipping all betas) see everything that changed.

## Creating a New Release

When creating a new release, follow this workflow:

### For Beta Releases

1. **Create beta release file**: `vX.Y.Z-beta.N.md`
1. **Document incremental changes** since previous beta (or since last stable if beta.1)
1. **Update CHANGELOG.md** with beta summary
1. **Update version** in `manifest.json`
1. **Update version** in `const.py` (VERSION constant)
1. **Create git tag**: `git tag -a vX.Y.Z-beta.N -m "Beta N of vX.Y.Z"`
1. **Push**: `git push && git push --tags`
1. **Create GitHub release**: `gh release create vX.Y.Z-beta.N --prerelease`

### For Stable Releases

1. **Create comprehensive release file**: `vX.Y.Z.md`
1. **Document ALL changes since last stable release**:
   - Review all beta release notes
   - Review all commits since last stable
   - Review all PRs merged since last stable
   - Include everything in comprehensive format
1. **Update CHANGELOG.md** with complete summary
1. **Update version** in `manifest.json` (remove -beta suffix)
1. **Update version** in `const.py` (remove -beta suffix)
1. **Create git tag**: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
1. **Push**: `git push && git push --tags`
1. **Create GitHub release**: `gh release create vX.Y.Z --latest`

## Release Note Template

### Beta Release Template

```markdown
# Release Notes - vX.Y.Z-beta.N

⚠️ **This is a BETA release** - Please test thoroughly before using in production

## What's New in This Beta

[Describe what's new since the previous beta]

## 🐛 Bug Fixes
- [List fixes in this beta]

## ✨ Features
- [List new features in this beta]

## 🧪 Testing Recommendations
[What should beta testers focus on?]

## ⚠️ Known Issues
[Any known issues in this beta]
```

### Stable Release Template

```markdown
# Release Notes - vX.Y.Z

## What's Changed Since vX.Y.Z (Last Stable)

[Comprehensive overview of ALL changes]

## 🐛 Critical Bug Fixes
[ALL bug fixes since last stable]

## ✨ Features
[ALL new features since last stable]

## ♻️ Code Quality Improvements
[ALL improvements since last stable]

## 📦 Dependencies
[ALL dependency updates since last stable]

## ⚠️ Breaking Changes
[ALL breaking changes since last stable]

## 🚀 Upgrade Notes
[Complete migration guide from last stable]

## 🎯 Summary of Beta Testing
[Overview of beta period if applicable]
```

Each release note file should include:

- Version number in title (with beta/stable indicator)
- Release date
- What's Changed summary (incremental for beta, comprehensive for stable)
- Relevant sections based on type of release
- Testing/upgrade recommendations
- Known issues (if any)
- Acknowledgments (if applicable)
- Links to CHANGELOG, full diff, and documentation

## File Naming Conventions

- Stable releases: `vX.Y.Z.md` (e.g., `v0.5.0.md`)
- Beta releases: `vX.Y.Z-beta.N.md` (e.g., `v0.5.0-beta.1.md`)
- Use lowercase 'v' prefix consistently
- Use semantic versioning (MAJOR.MINOR.PATCH)

## Navigation

- [← Back to CHANGELOG](../../CHANGELOG.md)
- [← Back to Repository Root](../../README.md)

## Questions?

If you have questions about the release process or documentation:

- Check existing release notes as examples
- Review [Keep a Changelog](https://keepachangelog.com/) guidelines
- Review [Semantic Versioning](https://semver.org/) specification
- Open an issue for clarification
