# Changelog

This file records shipped changes only.

TranscribeBench treats the commit that bumps the project version on `main` as the release boundary for each changelog entry.

## v1.0.0 - 2026-03-19

### Added
- Added archived benchmark snapshot support for dated benchmark artifacts.
- Added a dated 200-sample Dutch benchmark snapshot and matching benchmark config.
- Added `CHANGELOG.md` with versioned release entries only.
- Added `RELEASE_NOTES.md` with a per-release summary format.

### Changed
- Clarified the difference between mutable `latest` outputs and archived benchmark snapshots in the documentation.
- Refocused `TODO.md` on forward-looking release targets.
- Documented a lightweight major/minor/patch versioning policy and the rule that version-bump commits on `main` define release boundaries.

### Fixed
- Allowed archived benchmark `results.json` artifacts under `artifacts/results` to be committed.
