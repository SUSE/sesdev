# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Add Github Action to publish to OBS

### Fixed
- Handle Ctrl+C on deployment creation (PR #8)

### Changed
- Updated README.md on how to use an editable Python venv

## [1.0.3] - 2019-11-15
### Added
- README instructions about libvirt configuration (PR #4)

### Changed
- CLI subcommand `info` replaced by `show`.

### Fixed
- fix typo in `sesdev start --help` command (PR #6)

## [1.0.2] - 2019-11-15
### Fixed
- setup.py: missing libvirt engine template directory (PR #3)

## [1.0.1] - 2019-11-14
### Changed
- The OBS repo URL of sesdev package in README.md

### Fixed
- setup.py: missing template directories (PR #2)

## [1.0.0] - 2019-11-14
### Added
- `--libvirt-(user|storage-pool)` options to CLI.
- `--stop-before-deepsea-stage` option to CLI.
- `--cpus` option to CLI.
- `--ram` option to CLI.
- `--disk-size` option to CLI.
- `--repo` option to CLI.
- `--vagrant-box` option to CLI.
- openSUSE Leap 15.2 distro.
- SLES-15-SP2 distro.
- SES7 deployment based on SLES-15-SP2 (no Ceph cluster deployment yet).
- SES5 deployment based on SLES-12-SP3.
- SES6 deployment based on SLES-15-SP1.
- Octopus deployment based on Leap 15.2 (DeepSea is working 90%)
- Installation instructions to the README.md.
- openATTIC service tunneling support.
- Deployment description with `sesdev info <deployment_id>`.

### Changed
- Use `libvirt_use_ssh` instead of `libvirt_use_ssl` to configure SSH access.
- Vagrantfile template refactoring to support different deployment tools.
  Currently only DeepSea is implemented.
- Code refactoring to support other VM engines besides libvirt.
- CLI creation command changed to include the SES version we want to deploy.
  Now the command looks like `sesdev create <version> [options] <deployment_id>`.
- List deployments now return the status and the name of the nodes in each deployment.

### Fixed
- remove `qemu_use_session` vagrant-libvirt setting when packaging for Fedora 29.
- Use `RSA#exportKey` method to work with version 3.4.6 of pycrytodomex.
- Fixed type of `stop-before-stage` setting.
- Fix ssh command when libvirt is located in the localhost.
- Fix accepting salt-keys step in deployment by polling `salt-key -L`.
- Fix deployment status when `vagrant up` was never run.
- Only create deployment directory and files after rendering Vagranfile without errors.

## [0.2.2] - 2019-10-30
### Changed
- replaced `pycryptodome` library by `pycryptodomex`

### Fixed
- fix Fedora python rpm build macros in the specfile
- fix Fedora dependencies naming
- added buildrequires fdupes to spec file
- add buildrequires python3-rpm-macros for fedora in spec file
- add buildrequires python-rpm-macros for fedora in spec file
- fixed library dependencies
- explicitly set `qemu_use_session = false` in Vagrantfile to always use a system connection
- openSUSE requires python3-setuptools to run sesdev

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

[unreleased]: https://github.com/rjfd/sesdev/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/rjfd/sesdev/releases/tag/v1.0.3
[1.0.2]: https://github.com/rjfd/sesdev/releases/tag/v1.0.2
[1.0.1]: https://github.com/rjfd/sesdev/releases/tag/v1.0.1
[1.0.0]: https://github.com/rjfd/sesdev/releases/tag/v1.0.0
[0.2.2]: https://github.com/rjfd/sesdev/releases/tag/v0.2.2
[0.2.1]: https://github.com/rjfd/sesdev/releases/tag/v0.2.1
[0.2.0]: https://github.com/rjfd/sesdev/releases/tag/v0.2.0
[0.1.0]: https://github.com/rjfd/sesdev/releases/tag/v0.1.0
[0.0.1]: https://github.com/rjfd/sesdev/releases/tag/v0.0.1
