# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- fix Fedora python rpm build macros in the specfile
- fix Fedora dependencies naming
- added buildrequires fdupes to spec file

## [0.2.1] - 2019-10-29
### Fixed
- fixed `Source` and `Release` attributes in spec file

## [0.2.0] - 2019-10-29
### Added
- `--version` option to print the installed version.

### Changed
- version in `setup.py` is now parsed from `sesdev.spec`.

### Fixed
- `yaml.FullLoader` does not exist in older versions of PyYAML.
- unreleased link from CHANGELOG.md was pointing to keepchangelog repo.

## [0.1.0] - 2019-10-29
### Changed
- sesdev.spec: fixed sesdev dependencies
- sesdev.spec: fixed source URL
- sesdev.spec: set version number to 0.1.0

## [0.0.1] - 2019-10-29
### Added
- `sesdev` CLI tool with the following features:
  - create/destroy nautilus cluster based on openSUSE Leap 15.1.
  - ssh access to the nodes of the cluster.
  - port forwarding (ssh tunnel) of dashboard service.
- RPM spec file.
- Minimal README with a few usage instructions.
- The CHANGELOG file.

[unreleased]: https://github.com/rjfd/sesdev/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/rjfd/sesdev/releases/tag/v0.2.1
[0.2.0]: https://github.com/rjfd/sesdev/releases/tag/v0.2.0
[0.1.0]: https://github.com/rjfd/sesdev/releases/tag/v0.1.0
[0.0.1]: https://github.com/rjfd/sesdev/releases/tag/v0.0.1