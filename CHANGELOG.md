# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project aspires to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.9.1] - 2020-10-23

### Fixed
- sesdev --devel flag: let click deduct type (PR #550)

## [1.9.0] - 2020-10-23

### Added
- constant: add missing SLE-15-SP[12] Product repos (PR #530)
- Implement "sesdev upgrade" subcommand (PR #531)
- Implement "sesdev reboot DEP_ID NODE" command (PR #532)
- contrib/upgrade-demo-ses6-to-ses7.sh: add upgrade demo script (PR #535)
- provision.sh: add helper_scripts Jinja template (PR #540)

### Fixed
- exceptions: have SesDevException return optional exit code (PR #538)
- deployment: wait for rebooted node to complete boot sequence (PR #539)
- sesdev: fix --filestore regression (PR #545)
- cephadm/deployment_day_2.sh.j2: do not fail on defective --dry-run (PR #546)
- setup.cfg: include seslib/templates/cephadm/ directory in packaging (PR #548)

### Changed
- templates/zypper: do not install supportutils-plugin-ses in SES{5,6,7} (PR #526)

### Removed
- deepsea/nautilus_pre_stage_0.sh: refrain from patching DeepSea (PR #547)

## [1.8.0] - 2020-10-08

### Added
- Add support for IPv6 (PR #56)
- contrib/deepsea_drive_replace.sh: new test script (PR #306)
- ceph_salt: deploy and smoke-test Prometheus (PR #418)
- ceph-salt: deploy and smoke-test Grafana (PR #475) 
- ceph-salt: deploy and smoke-test alertmanager (PR #480)
- ceph-salt: deploy and smoke-test node-exporter (PR #496)
- Support official Vagrant boxes from Vagrant Cloud (PR #476)
- new msgr2 secure options (PR #481)
- Add ability to deploy Ceph on Ubuntu "Bionic Beaver" 18.04 (PR #486)
- add label for ses deployment on caasp (PR #488)
- Implement --no-provision option to deploy "bare" VMs (PR #490)
- Implement "sesdev link" for linking two clusters (PR #498)
- Implement "sesdev status" subcommand (PR #502)
- Implement "sesdev show DEP_ID --nodes-with-role=ROLE" (PR #506)
- Make "sesdev box list" and "sesdev box remove" accept globs (PR #517)
- create: implement --fqdn option, specify FQDN when appropriate (PR #519, PR #522)

### Removed
- replace --deploy/--no-deploy option with --provision/--no-provision (PR #490)
- caasp4: remove anti-affinity for mons for single node (PR #495) 
- Revert "ceph_salt_deployment: add 1-minute grace period" (PR #521)

### Fixed
- ceph-salt: set some network-related config params explicitly (PR #482)
- deployment: do not assert if starting an existing deployment (PR #493)
- deployment: do not populate public_network with "0/24" (PR #512)
- qa: wait for grafanas to show up before counting them (PR #514)
- qa: wait longer for cluster to become healthy (PR #515)
- Add makecheck-specific repos only in "sesdev create makecheck" (PR #520)

### Changed
- zypper: install rbd-nbd on all Leap 15.2/SLE-15-SP2 nodes (PR #484)
- Update pacific repos (PR #489)
- qa/nfs: do not attempt to mount NFS export on "pacific" (PR #492)
- deployment: use "vagrant up --provision" to start cluster (PR #501)
- cleanup: move cephadm Day 2 provisioner to its own subdirectory (PR #513) 
- tox: run pip with --use-feature=2020-resolver (PR #516)

## [1.7.0] - 2020-09-13

### Added
- ceph_salt_deployment: do "ceph orch apply --dry-run" (PR #406)
- single node CaaSP cluster (PR #427)
- If --ssd option is given, attempt to make first additional disk
  non-rotational (PR #448)
- Implement "sesdev box remove --all" feature (PR #451)
- qa: support openSUSE Tumbleweed (PR #457)

### Removed
- Drop ceph-salt '/system_update' config (PR #447)

### Fixed
- replace-mgr-modules: refrain from introducing Python 2 (PR #431)
- deepsea: add ganesha roles to policy.cfg (PR #437)
- deepsea: properly recognize deprecated ganesha role (PR #442)
- ceph_salt_deployment: prevent Vagrant 2.2.10+ from deleting master node (PR #452)
- provision.sh: disable host checking when SSHing within the cluster (PR #455)
- ceph_salt_deployment: explicitly create mds service (PR #458)
- contrib/standalone.sh: adapt to create always returning 0 (PR #460)
- deepsea_deployment: really stop before Stage 0 (PR #462)
- ceph-salt: Fix ceph image path config (PR #465)
- ceph_salt_deployment: always wait for OSDs to appear (PR #466)
- ceph_salt_deployment: deploy MDSs according to documentation (PR #468)

### Changed
- ceph_salt_deployment: extend OSD deployment timeout (PR #432)
- caasp: set num_disks in same way as for ceph deployments (PR #434)
- vet_configuration: vet caasp4 roles more carefully (PR #435)
- cephadm: allow preparation of cluster for manual deployment (PR #436)
- caasp: update to caasp 4.5 (PR #438)
- deployment: disks even when explicit storage role not given (PR #439)
- cleanup: move code out of Deployment/_generate_nodes() (PR #441)
- ceph-salt: enable user to control which nodes get "admin" role (PR #443)
- cleanup: streamline unit testing and code linting (PR #444)
- ceph_salt_deployment: tolerate additional bootstrap MONs/MGRs that we didn't
  ask for (PR #449)
- ceph_salt_deployment: expose ceph-salt errors early (PR #456)
- ceph-salt: bootstrap minion no longer required to have admin role (PR #461)
- Split ceph_salt_deployment.sh into "Day 1" and "Day 2" scripts (PR #471)

## [1.6.1] - 2020-08-11

### Fixed
- ceph_salt_deployment: implement "--stop-before-ceph-orch-apply" (PR #415)
- settings: rename straggler version_os_repo_mappings (PR #419)
- setup.cfg: fix "options.package_data" file list (PR #424)

### Changed
- sesdev: non-create, non-box functions in alphabetical order (PR #414)
- Unify naming of role-related constants (PR #416)
- CaaSP: remove hard dependency on loadbalancer (PR #422)

## [1.6.0] - 2020-07-26

### Added
- sesdev: implement --dry-run for create commands (PR #384)
- ceph_salt_deployment: use mgr/nfs CLI to deploy NFS Ganesha (PR #385)
- 'sesdev replace-mgr-modules' should also replace 'bin/cephadm' (PR #387)
- qa: enable dashboard branding test on {octopus,ses7} (PR #392)
- zypper: remove rsync if it's installed in the Vagrant Box (PR #395)
- ceph_salt_deployment: "ceph -s" when OSDs fail to come up (PR #409)
- deployment: run supportconfig with 1-hour timeout (PR #410)
- provision.sh: persist the journal (PR #411)

### Removed
- ses5: stop patching srv/salt/ceph/time/ntp/default.sls (PR #407)

### Changed
- split seslib/__init__.py into several smaller files (PR #377, #380)
- provision.sh: add all repos before installing packages (PR #381)
- Refactor seslib/templates/provision.sh (PR #383)
- deployment/status: aggregate global parameters (PR #393)
- Improve the "show" subcommand and deployment configuration listing (PR #399)
- Change --repo-priority default from "True" to "False" (PR #400)
- seslib: revamp custom_repo (PR #402)
- seslib/deployment: try to destroy the whole cluster at once (PR #403)
- log: print log messages to the screen under certain circumstances (PR #404)
- Rename "version_os_repo_mapping" to "version_devel_repos" (PR #408)
- ceph_salt_deployment.sh: extend OSD timeout (PR #413)

### Fixed
- qa/common/rgw: fix curl try-wait (PR #379)
- sesdev: use Luminous roles for SES5 (PR #382)
- ceph_salt_deployment: fix off-by-one error in OSDs wait loop (PR #394)
- sesdev: fix --non-interactive/--force handling (PR #395)
- deployment: generate static networks on create only (PR #401)

## [1.5.0] - 2020-07-03

### Added
- cephadm iSCSI deployment (PR #300)
- "--filestore" option to deploy OSDs with FileStore (PR #341)
- "--devel/--product" option and add-repo subcommand (PR #351)
- qa: superficial test for presence of dashboard branding (PR #374)
- qa: add IGW to existing tests (PR #372)

### Changed
- provisioning: set fqdn through vagrant and leave /etc/hosts alone (PR #199)
- no longer support nautilus deployment in Tumbleweed (PR #352)
- ceph_salt_deployment.sh: reduce number of "ceph orch apply" calls (PR #363)
- sesdev: raise exception if --roles combined with --single-node (PR #376)
- cleanup: replace "grep | wc --lines" with "grep --count" (PR #375)

### Fixed
- makecheck: reasonable defaults for Ceph repo/branch (PR #277)
- provision.sh: set up SSH keys earlier (PR #361)
- provision.sh: avoid endless while loop (PR #365)
- sesdev: sanitize makecheck deployment IDs (PR #371)
- doc: Update the example Deployment id in sesdev help (PR #378)
- qa/systemctl_test: better error message when FSID omitted (PR #373)
- qa/rgw: run curl command in try-wait loop to ping RGW (PR #370)
- qa: do not wait for non-existent daemons to start (PR #368)
- qa: get RGW port from /etc/ceph/ceph.conf (PR #353)

## [1.4.0] - 2020-06-20

### Added
- "replace-mgr-modules" subcommand (PR #24)
- "replace-ceph-salt" subcommand (PR #331)
- NFS (Ganesha) server deployment in {octopus,ses7,pacific} (PR #337)
- qa: curl-based RGW smoke test (PR #344)
- qa: systemctl-based smoke test (PR #347)

### Removed
- "--use-deepsea" option for {ses7,octopus,pacific} (PR #334)

### Fixed
- ceph_salt_deployment: fix use_salt=True deployment (PR #326)
- sync_clocks.sh: put chronyc calls in try_wait (PR #328)
- qa: tolerate +1 MGRs in number_of_nodes_actual_vs_expected_test (PR #332)

### Changed
- ceph_salt_deployment: deploy OSDs from YAML (ServiceSpec) file (PR #203)
- makecheck: possibly prophylactically downgrade libncurses6 (PR #325)
- explicit "admin" role no longer allowed (PR #330)
- seslib: move boilerplate ssh options into a staticmethod (PR #333)
- deployment IDs are now vetted for correctness (PR #335)
- seslib: generate comma-separated lists of nodes with each role (PR #345)
- If not provided explicitly via the "--domain" option, new deployments now
  default to ".test" instead of ".com" as the cluster TLD (PR #350)

## [1.3.0] - 2020-05-25

### Added
- octopus/ses7: added "--stop-before-ceph-orch-apply" function (PR #301)
- Implement RGW deployment in octopus, ses7 (PR #314)
- ceph_salt_deployment: do not force user to change dashboard pw (PR #315)
- makecheck: possibly prophylactically downgrade libudev1 (PR #317)
- contrib/standalone.sh: --no-stop-on-failure option (PR #318)
- ceph_salt_deployment: make use of 'cephadm' role (PR #319)

### Removed
- octopus/ses7: removed "--deploy-mons", "--deploy-mgrs", "--deploy-osds",
  "--deploy-mdss" (replaced by "--stop-before-ceph-orch-apply") (PR #301)
- seslib: drop Containers module from SES7 deployment (PR #303)
- provision.sh: remove curl RPM from the environment (PR #311)

### Fixed
- Fixed "sesdev create caasp4" default deployment by disabling multi-master
  (PR #302)
- ceph_salt_deployment: do not deploy MDS if no mds roles present (PR #313)
- caasp: do not install salt (PR #320)
- supportconfig: handle both scc and nts tarball prefixes (PR #323)
- qa: work around cephadm MGR co-location issue (PR #324)

### Changed
- seslib: convert certain public methods into private (PR #309)
- caasp4: rename "storage" role to "nfs" and drop it from default 4-node
  deployment (PR #310)

## [1.2.0] - 2020-05-04

### Added
- deepsea_deployment: pre-create Stage 4 pools (PR #298)

### Fixed
- setup.cfg: do not break Tumbleweed RPM install (PR #297)

### Changed
- ceph_salt_deployment.sh: rip out time sync code (PR #289)
- Rename '--stop-before-ceph-salt-deploy' to '--stop-before-ceph-salt-apply' (PR
  #290)

## [1.1.12] - 2020-04-28

### Added
- provision.sh: enable autorefresh on all repos (PR #288)

### Fixed
- seslib: fix "Unused argument" linter warning (PR #286)
- provision.sh.j2: Properly prepare CaaSP nodes (PR #283)
- ceph_salt_deployment: really sync clocks (PR #285)

### Changed
- Rename 'ceph-salt deploy' to 'ceph-salt apply' (PR #280)

## [1.1.11] - 2020-04-24

### Added
- Implement feature "sesdev create makecheck" (PR #236)
- Deployment: silently add "master" and "bootstrap" roles (PR #254)
- sesdev: implement "sesdev list --format json" and PrettyTable-based
  "sesdev list" (PR #259)

### Fixed
- qa: fix maybe_wait_for_mdss test (PR #262)
- provision.sh: remove Non-OSS repos on openSUSE (PR #265)
- sesdev: support Click 6.7 (PR #268)
- seslib: more robust dashboard tunnelling (PR #274)
- deepsea: "openattic" role needs Stage 4 (PR #275)
- provision.sh: refactor while loops and fix packaging-related breakage
  (PR #279)

### Changed
- Remove "disable cephadm bootstrap" functionality (PR #261)
- Rename --deepsea-cli and --ceph-salt-deploy options to --salt (PR #267)

## [1.1.10] - 2020-04-17

### Added
- ceph_salt_deployment: sync clocks after deployment (PR #187)
- ceph_salt_deployment: fetch GitHub PRs when needed (PR #197)
- New deployment type "pacific" using packages/containers built from upstream
  Ceph "master" branch (PR #200)
- README.md: Needed packages for all major distros (PR #209)
- sesdev: systemically vet roles on create (PR #215)
- templates: extend --qa-test to DeepSea-deployed versions (PR #230)
- sesdev: make deployment_id argument optional (PR#235)
- sesdev: Globbing for "stop", "start", and "destroy" (PR #238)
- new --synced-folder option to NFS mount directories (PR #247)
- ses7, octopus, pacific: Deploy MDSs (PR #258)

### Fixed
- deepsea_deployment: run Stage 4 only if justified by roles (PR #205)
- seslib: install sesdev-generated keypair under non-default name (PR #207) 
- Jenkinsfile.integration: Retry jenkins slave deletion (PR #214)
- ceph_salt_deployment: use --prefix /usr with "pip install" (PR #221)
- deepsea_deployment: check if drive_groups.yml exists (PR #229)
- seslib: force ses5 prometheus node to master (PR #232)
- provision.sh: reinstall certain packages from the update repos (PR #243)
- ceph_salt_deployment: do not provision client-only nodes (PR #246)

### Changed
- ceph_salt_deployment: move OSD deployment to sesdev (PR #186)
- ceph_salt_deployment: use sesdev to deploy MONs and MGRs (PR #189)
- sesdev: uniform --force/--non-interactive (PR #201)
- ceph_salt_deployment: make it easier to install ceph-salt from source (PR #210)
- seslib: make all str-type settings default to the empty string (PR #217)
- ceph_salt_deployment: Use quoted string to set bootstrap configs (PR #224)
- ceph_salt_deployment: use lower-case on config nodes (PR #226)
- ceph_salt_deployment: do not refresh/sync pillar data (PR #227)
- templates: move test.ping try-wait into a separate file (PR #234)

## [1.1.9] - 2020-03-26

### Added
- config.yaml: enable setting of repo priority in version_os_repo_mapping (PR #163)
- Add a bootstrap.sh script and document how to use it (PR #165)
- provision.sh: add SUSE:CA repo on ses5 (PR #166)
- Implement feature: "sesdev ssh DEP_ID NODE_ID COMMAND" (PR #175)
- Implement feature: "sesdev supportconfig DEPLOYMENT_ID NODE_ID" (PR #176)
- Implement feature: --encrypted-osds (PR #192)

### Fixed
- provision.sh: do not fail ses5 deployment if ntp not installed (PR #173)
- ceph_salt_deployment.sh: adapt Drive Group string to new syntax (PR #178)
- qa/health-ok.sh: wait for OSD nodes to show up (PR #180)
- bootstrap.sh: explicitly use Python 3 (PR #195)

### Changed
- Vagrantfile,sesdev.spec: require vagrant > 2.2.2 (PR #167)
- Jenkinsfile.integration:
    - Add timeout for "sesdev create" (PR #169)
    - Parametrize ceph-salt repo and branch (PR #179)
    - use bootstrap script and and parameter for extra repo URLs (PR #182)
    - Be able to set custom job name/desc (PR #184)
    - Add colorful output when running sesdev (PR #196)
- Use "filesystems:ceph:octopus:upstream" for default cephadm/container build (PR #170)
- Set "osd crush chooseleaf type = 0" via bootstrap ceph.conf in very small clusters (PR #183)
- ceph_salt_deployment.sh: Fetch github PRs when installing from src (PR #190)

## [1.1.8] - 2020-03-13

### Added
- seslib: remove host's virtual networks on destroy (PR #102)
- Jenkinsfile.integration for PR testing (PR #118, PR #154) 
- prometheus and alertmanager tunnels (PR #148)
- tests: enable unit testing via tox (PR #151)

### Fixed
- seslib: stop printing misleading device names (PR #150)

### Changed
- seslib: Set admin roles for octopus (PR #158)
- Change "admin" role semantics and make roles configurable (PR #161)
- Allow user to override parts of OS_REPOS, VERSION_OS_REPO_MAPPING, and IMAGE_PATHS (PR #146)

## [1.1.7] - 2020-03-09

### Added
- ceph_salt_deployment: run "ceph-salt status" after "ceph-salt config ls"
  (PR #138)
- Let --debug run "vagrant up/destroy" in debug mode (PR #89)

### Fixed
- qa: fix path to qa scripts for RPM case (PR #141)
- ceph_salt_deployment: honor --no-deploy-osds option (PR #143)

### Changed
- spec: disable RH/Fedora Python dependendency generator (PR #140)
- spec: always install sesdev-qa RPM along with sesdev (PR #144)

## [1.1.6] - 2020-03-05

### Added
- sesdev: add --non-interactive option to "sesdev create" (PR #125)
- Implement "sesdev qa-test" command (PR #129)
- qa: assert "ceph versions" matches "ceph --version" (PR #131)

### Fixed
- seslib: correct downstream container for "sesdev create {ses7,octopus}" (PR #130)
- provision.sh: remove Python 2 so it doesn't pollute the environment (PR #133)

### Changed
- Rename --ceph-container-image to --image-path (PR #115)
- provision: install "command-not-found", "supportutils", etc. in test environments (PR #123)
- Return with a non-zero exit code in a failure case (PR #127)
- seslib: rename --deploy-bootstrap to --cephadm-bootstrap (PR #137)

## [1.1.5] - 2020-02-26

### Fixed
- sesdev.spec: use standard ordering of sections
- sesdev: give the user a way to specify --no-deploy-... (PR #120)
- seslib: fix --no-deploy-mgrs option not working (PR #122)

## [1.1.4] - 2020-02-26

### Fixed
- sesdev.spec: properly package /usr/share/sesdev directory
  (follow-on fix for PR #112)

## [1.1.3] - 2020-02-25

### Changed
- Rename ceph-bootstrap to ceph-salt (PR #114)
- Migrate ceph-bootstrap-qa to sesdev (part 2) (PR #112)
- provision: remove which RPM from test environment (PR #113)
- ceph_salt_deployment: disable system update and reboot (PR #117)
- seslib: by default, a mgr for every mon (PR #111)

## [1.1.2] - 2020-02-17

### Added
- Implement "vagrant box list" and "vagrant box remove" (PR #69)
- Allow user to specify custom private key file for remote libvirt (PR #71)
- spec: add Fedora-specific Requires (PR #77)
- Pillar is now automatically configured by ceph-bootstrap (PR #78)
- Implement "sesdev scp" feature (PR #101)
- Implement "sesdev create caasp4" feature (PR #103)

### Fixed
- Revamp --num-disks handling (PR #65)
- Miscellaneous spec file cleanups and bugfixes (PR #72)
- several fixes for octopus/ses7 deployment (PR #76)
- Remove any orphaned images after destroy (PR #81)
- seslib: fix Ceph repos for ses5, ses6, ses7 (PR #83)
- tools/run_async: decode stderr bytes (PR #88)
- libvirt/network: autostart networks per default (PR #93)
- Fix NTP issue that was causing SES5 deployment to fail (PR #108)

### Changed
- ceph_bootstrap_deployment: "ceph-bootstrap -ldebug deploy" (PR #68)
- Increase chances of getting the latest ses7 packages (PR #84)
- ceph_bootstrap_deployment: log cephadm and ceph-bootstrap version (PR #86)
- ceph_bootstrap: restart salt-master after ceph-bootstrap installation (PR #87)
- seslib: add SES7 Internal Media when --qa-test given (PR #90)

## [1.1.1] - 2020-01-29
### Added
- Octopus and SES7 deployment with ceph-bootstrap (PR #28)
- Implement --repo-priority / --no-repo-priority (PR #19)
- Add option for predefined libvirt networks (PR #39) 
- qa: initial qa integration (PR #46)

### Fixed
- When deploying ses5 with explicit --roles, do not add openattic (PR #23)
- Enable display of manpages (PR #33)
- ceph_bootstrap_deployment.sh: Also set -e (PR #35)
- vagrant: generate random serial number for each attached disk (PR #50)
- ceph_bootstrap_deployment: ensure minions are responding (PR #52)

### Changed
- Add node info to SSH tunnel command (PR #27)
- Display amount of deployed VMs in status output (PR #31)
- Enable linter via travis (PR #38)
- ceph-bootstrap: 'ceph-salt-formula' moved to 'ceph-bootstrap' (PR #44)
- ceph_bootstrap: use "ceph-bootstrap deploy" command to run ceph-salt formula
  (PR #62)

## [1.1.0] - 2019-11-27
### Added
- Add Github Action to publish to OBS (PR #10).
- SUMA deployment in `octopus` version (PR #14).

### Fixed
- Handle Ctrl+C on deployment creation (PR #8)
- seslib: fixed 100% cpu usage when deploying cluster (PR #16).

### Changed
- Updated README.md on how to use an editable Python venv (PR #15).
- cli: `list` subcommand now shows the version of each deployment (PR #12).
- octopus and ses7 versions now use the OBS repo filesystems:ceph:master:upstream that
  is updated in a daily basis (PR #13).

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

[unreleased]: https://github.com/SUSE/sesdev/compare/v1.9.1...HEAD
[1.9.1]: https://github.com/SUSE/sesdev/releases/tag/v1.9.1
[1.9.0]: https://github.com/SUSE/sesdev/releases/tag/v1.9.0
[1.8.0]: https://github.com/SUSE/sesdev/releases/tag/v1.8.0
[1.7.0]: https://github.com/SUSE/sesdev/releases/tag/v1.7.0
[1.6.1]: https://github.com/SUSE/sesdev/releases/tag/v1.6.1
[1.6.0]: https://github.com/SUSE/sesdev/releases/tag/v1.6.0
[1.5.0]: https://github.com/SUSE/sesdev/releases/tag/v1.5.0
[1.4.0]: https://github.com/SUSE/sesdev/releases/tag/v1.4.0
[1.3.0]: https://github.com/SUSE/sesdev/releases/tag/v1.3.0
[1.2.0]: https://github.com/SUSE/sesdev/releases/tag/v1.2.0
[1.1.12]: https://github.com/SUSE/sesdev/releases/tag/v1.1.12
[1.1.11]: https://github.com/SUSE/sesdev/releases/tag/v1.1.11
[1.1.10]: https://github.com/SUSE/sesdev/releases/tag/v1.1.10
[1.1.9]: https://github.com/SUSE/sesdev/releases/tag/v1.1.9
[1.1.8]: https://github.com/SUSE/sesdev/releases/tag/v1.1.8
[1.1.7]: https://github.com/SUSE/sesdev/releases/tag/v1.1.7
[1.1.6]: https://github.com/SUSE/sesdev/releases/tag/v1.1.6
[1.1.5]: https://github.com/SUSE/sesdev/releases/tag/v1.1.5
[1.1.4]: https://github.com/SUSE/sesdev/releases/tag/v1.1.4
[1.1.3]: https://github.com/SUSE/sesdev/releases/tag/v1.1.3
[1.1.2]: https://github.com/SUSE/sesdev/releases/tag/v1.1.2
[1.1.1]: https://github.com/SUSE/sesdev/releases/tag/v1.1.1
[1.1.0]: https://github.com/SUSE/sesdev/releases/tag/v1.1.0
[1.0.3]: https://github.com/SUSE/sesdev/releases/tag/v1.0.3
[1.0.2]: https://github.com/SUSE/sesdev/releases/tag/v1.0.2
[1.0.1]: https://github.com/SUSE/sesdev/releases/tag/v1.0.1
[1.0.0]: https://github.com/SUSE/sesdev/releases/tag/v1.0.0
[0.2.2]: https://github.com/SUSE/sesdev/releases/tag/v0.2.2
[0.2.1]: https://github.com/SUSE/sesdev/releases/tag/v0.2.1
[0.2.0]: https://github.com/SUSE/sesdev/releases/tag/v0.2.0
[0.1.0]: https://github.com/SUSE/sesdev/releases/tag/v0.1.0
[0.0.1]: https://github.com/SUSE/sesdev/releases/tag/v0.0.1
