import fnmatch
import json
import logging
from os import environ, path
import re
import sys
import requests

from prettytable import PrettyTable

import click
import pkg_resources

from sesdev.box import box_list_handler, box_remove_handler
from seslib.constant import Constant
from seslib.deployment import Deployment
from seslib.exceptions import \
                              SesDevException, \
                              AddRepoNoUpdateWithExplicitRepo, \
                              BoxDoesNotExist, \
                              CmdException, \
                              DebugWithoutLogFileDoesNothing, \
                              NodeDoesNotExist, \
                              NoExplicitRolesWithSingleNode, \
                              NoNodeWithRole, \
                              OptionFormatError, \
                              OptionNotSupportedInContext, \
                              OptionNotSupportedInVersion, \
                              OptionValueError, \
                              SSHCommandReturnedNonZero, \
                              VersionNotKnown, \
                              YouMustProvide
from seslib.log import Log
from seslib.settings import Settings
from seslib import tools
from seslib.zypper import ZypperRepo


logger = logging.getLogger(__name__)


def sesdev_main():
    Constant.init_path_to_qa(__file__)
    try:
        # pylint: disable=unexpected-keyword-arg
        cli(prog_name='sesdev')
    except SesDevException as ex:
        logger.exception(ex)
        click.echo(str(ex))
        if ex.args[0]:
            return int(ex.args[0])
        return 1
    return 0


def _decorator_composer(decorator_list, func):
    if not decorator_list:
        return func
    head, *tail = decorator_list
    return _decorator_composer(tail, head(func))


def libvirt_options(func):
    click_options = [
        click.option('--libvirt-host', type=str, default=None,
                     help='Hostname of the libvirt machine'),
        click.option('--libvirt-user', type=str, default=None,
                     help='Username for connecting to the libvirt machine'),
        click.option('--libvirt-storage-pool', type=str, default=None,
                     help='Libvirt storage pool'),
        click.option('--libvirt-private-key-file', type=str, default=None,
                     help='Path to SSH private key to use when building the qemu+ssh connection'),
        click.option('--libvirt-networks', type=str, default=None,
                     help='Existing libvirt networks to use (single or comma separated list)'),
    ]
    return _decorator_composer(click_options, func)


def deepsea_options(func):
    click_options = [
        click.option('--salt/--deepsea-cli', default=False,
                     help='Use "salt-run" (instead of DeepSea CLI) to execute DeepSea stages'),
        click.option('--stop-before-deepsea-stage', type=int, default=None,
                     help='Allows to stop deployment before running the specified DeepSea stage'),
        click.option('--deepsea-repo', type=str, default=None, help='DeepSea Git repo URL'),
        click.option('--deepsea-branch', type=str, default=None, help='DeepSea Git branch'),
    ]
    return _decorator_composer(click_options, func)


def ceph_salt_options(func):
    click_options = [
        click.option('--stop-before-ceph-salt-config', is_flag=True, default=False,
                     help='Stop deployment before creating ceph-salt configuration'),
        click.option('--stop-before-ceph-salt-apply', is_flag=True, default=False,
                     help='Stop deployment before applying ceph-salt configuration'),
        click.option('--stop-before-cephadm-bootstrap', is_flag=True, default=False,
                     help='Stop deployment before running "cephadm bootstrap"'),
        click.option('--stop-before-ceph-orch-apply', is_flag=True, default=False,
                     help='Stop deployment before applying ceph orch service spec'),

        click.option('--ceph-salt-repo', type=str, default=None,
                     help='ceph-salt Git repo URL'),
        click.option('--ceph-salt-branch', type=str, default=None,
                     help='ceph-salt Git branch'),

        click.option('--image-path', type=str, default=None,
                     help='registry path from which to download Ceph base container image '
                          '(deprecated)'),
        click.option('--ceph-image-path', type=str, default=None,
                     help='registry path from which to download Ceph base container image'),
        click.option('--grafana-image-path', type=str, default=None,
                     help='registry path from which to download Grafana container image'),
        click.option('--prometheus-image-path', type=str, default=None,
                     help='registry path from which to download Prometheus container image'),
        click.option('--node-exporter-image-path', type=str, default=None,
                     help='registry path from which to download Node-Exporter container image'),
        click.option('--alertmanager-image-path', type=str, default=None,
                     help='registry path from which to download Alertmanager container image'),
        click.option('--keepalived-image-path', type=str, default=None,
                     help='registry path from which to download Keepalived container image'),
        click.option('--haproxy-image-path', type=str, default=None,
                     help='registry path from which to download HAProxy container image'),
        click.option('--snmp-gateway-image-path', type=str, default=None,
                     help='registry path from which to download SNMP-Gateway container image'),

        click.option('--salt/--ceph-salt', default=False,
                     help='Use "salt" (instead of "ceph-salt") to run ceph-salt formula'),
        click.option('--msgr2-secure-mode', is_flag=True, default=False,
                     help='enable "ms_*_mode" options to secure'),
        click.option('--msgr2-prefer-secure', is_flag=True, default=False,
                     help='enable "ms_*_mode" to prefer secure (change to "secure crc")'),
    ]
    return _decorator_composer(click_options, func)


def common_create_options(func):
    click_options = [
        click.option('--roles', type=str, default=None,
                     help='List of roles for each node. Example for two nodes: '
                          '[master, client, prometheus],[storage, mon, mgr]'),
        click.option('--os', type=click.Choice(['leap-15.1',
                                                'leap-15.2',
                                                'leap-15.3',
                                                'leap-15.4',
                                                'tumbleweed',
                                                'sles-15-sp1',
                                                'sles-15-sp2',
                                                'sles-15-sp3',
                                                'ubuntu-bionic']),
                     default=None, help='OS (open)SUSE distro'),
        click.option('--provision/--no-provision',
                     default=True,
                     help="Whether to provision the VMs (e.g., deploy Ceph on them) "
                          "after creation"
                    ),
        click.option('--cpus', default=None, type=int,
                     help='Number of virtual CPUs for the VMs'),
        click.option('--ram', default=None, type=int,
                     help='Amount of RAM for each VM in gigabytes'),
        click.option('--disk-size', default=None, type=int,
                     help='Size in gigabytes of storage disks (used by OSDs)'),
        click.option('--num-disks', default=None, type=int,
                     help='Number of storage disks in OSD nodes'),
        click.option('--single-node/--no-single-node', default=False,
                     help='Deploy a single node cluster. Overrides --roles'),
        click.option('--repo', multiple=True, default=None,
                     help='Custom zypper repo URL. The repo will be added to each node.'),
        click.option('--repo-priority/--no-repo-priority', default=False,
                     help="Automatically set priority on custom zypper repos"),
        click.option('--devel/--product', default=True,
                     help=("Include devel repo, if applicable. By default, the devel repos will be "
                           "used.")),
        click.option('--qa-test/--no-qa-test', 'qa_test_opt', default=False,
                     help="Automatically run integration tests on the deployed cluster"),
        click.option('--scc-user', type=str, default=None,
                     help='SCC organization username'),
        click.option('--scc-pass', type=str, default=None,
                     help='SCC organization password'),
        click.option('--domain', type=str, default='{}.test',
                     help='Domain name to use'),
        click.option('--non-interactive', '-n', '--force', '-f', is_flag=True, default=False,
                     help='Do not ask the user if they really want to'),
        click.option('--encrypted-osds', is_flag=True, default=False,
                     help='Deploy OSDs encrypted'),
        click.option('--bluestore/--filestore', is_flag=True, default=True,
                     help='Deploy OSDs with BlueStore or FileStore'),
        click.option('--synced-folder', type=str, default=None, multiple=True,
                     help='Set synced-folder to be mounted on the master node. <str:dest>'),
        click.option('--dry-run/--no-dry-run', is_flag=True, default=False,
                     help='Dry run (do not create any VMs)'),
        click.option('--ssd', is_flag=True, default=False,
                     help='On VMS with additional disks, make one disk non-rotational'),
        click.option('--fqdn', is_flag=True, default=False,
                     help='Make \'hostname\' command return FQDN'),
        click.option('--apparmor/--no-apparmor', is_flag=True, default=True,
                     help='Enable/disable AppArmor'),
        click.option('--rgw-ssl/--no-rgw-ssl', is_flag=True, default=False,
                     help='Deploy RGW with SSL'),
    ]
    return _decorator_composer(click_options, func)


def ipv6_options(func):
    click_options = [
        click.option('--ipv6', is_flag=True, default=False,
                     help='Configure IPv6 addresses. This option requires "Accept Router '
                          'Advertisements" to be set to 2. You can change it by running '
                          '"sysctl -w net.ipv6.conf.<if>.accept_ra=2" where '
                          '<if> is the network interface used by libvirt for network '
                          'forwarding, or "all" to apply to all interfaces.',),
    ]
    return _decorator_composer(click_options, func)


def _parse_roles(roles):
    roles = "".join(roles.split())
    if roles.startswith('[[') and roles.endswith(']]'):
        roles = roles[1:-1]
    roles = roles.split(",")
    Log.debug("_parse_roles: raw roles from user: {}".format(roles))
    Log.debug("_parse_roles: pre-processed roles array: {}".format(roles))
    _roles = []
    _node = None
    for role in roles:
        if role.startswith('['):
            _node = []
            if role.endswith(']'):
                role = role[1:-1]
                if role:
                    _node.append(role)
                _node.sort()
                _roles.append(_node)
            else:
                role = role[1:]
                _node.append(role)
        elif role.endswith(']'):
            role = role[:-1]
            _node.append(role)
            _node.sort()
            _roles.append(_node)
        else:
            _node.append(role)
    return _roles


def _print_log(output):
    sys.stdout.write(output)
    sys.stdout.flush()


def _silent_log(_):
    pass


def _abort_if_false(ctx, _, value):
    if not value:
        ctx.abort()


def _maybe_gen_dep_id(version, dep_id, settings_dict):
    if not dep_id:
        single_node = settings_dict['single_node'] if 'single_node' in settings_dict else False
        dep_id = version
        if single_node:
            dep_id += "-mini"
    return dep_id


def _maybe_munge_repo_url(repo_url):
    retval = repo_url
    match = re.search(r'(http.+\/).+\.repo$', repo_url)
    if match:
        retval = match.group(1)
    return retval


@click.group()
@click.option('-w', '--work-path', required=False,
              type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help='Filesystem path to store deployments')
@click.option('-c', '--config-file', required=False,
              type=click.Path(exists=True, dir_okay=False, file_okay=True),
              help='Configuration file location')
@click.option('-d', '--debug/--no-debug', default=False,
              help='Whether to emit DEBUG-level log messages')
@click.option('--log-file', type=str, default=None,
              help='Whether to append log messages to a file (and which file)')
@click.option('--vagrant-debug/--no-vagrant-debug', default=False,
              help='Whether to run vagrant with --debug option')
@click.option('-v', '--verbose/--no-verbose', default=False,
              help='Whether to emit INFO- and WARNING-level log messages')
@click.version_option(pkg_resources.get_distribution('sesdev'), message="%(version)s")
def cli(
        config_file=None,
        debug=None,
        log_file=None,
        vagrant_debug=None,
        verbose=None,
        work_path=None,
):
    """
    Welcome to the sesdev tool.

    Usage examples:

    # Deployment of single node SES6 cluster:

        $ sesdev create ses6 --single-node my-ses6-cluster

    # Deployment of Octopus cluster where each storage node contains 4 10G disks for
OSDs:

        \b
$ sesdev create octopus --roles="[master, mon, mgr], \\
       [storage, mon, mgr, mds], [storage, mon, mds]" \\
       --num-disks=4 --disk-size=10 my-octopus-cluster

    """
    Constant.LOG_FILE = bool(log_file)  # set once here, never to change again
    if log_file:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            filename=log_file, filemode='w',
                            level=logging.DEBUG if debug else logging.INFO)
    else:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            level=logging.CRITICAL)
        # note: we can't go any lower than CRITICAL here without causing
        # Python tracebacks to be barfed out to the screen

    Constant.DEBUG = bool(debug)  # set once here, never to change again
    Constant.VERBOSE = bool(verbose)  # set once here, never to change again

    if debug:
        if not Constant.LOG_FILE:
            raise DebugWithoutLogFileDoesNothing()
        Constant.VERBOSE = True

    if Constant.DEBUG:
        Log.info("Debug mode: ON")
    else:
        Log.debug("Debug mode: OFF")

    if Constant.VERBOSE:
        Log.info("Verbose mode: ON")
    else:
        Log.debug("Verbose mode: OFF")

    Constant.VAGRANT_DEBUG = bool(vagrant_debug)  # set once here, never to change again
    if vagrant_debug:
        Log.info("vagrant will be run with --debug option")

    if work_path:
        Log.info("Working path: {}".format(work_path))
        Constant.A_WORKING_DIR = work_path  # set once here, never to change again

    if config_file:
        Log.info("Config file: {}".format(config_file))
        Constant.CONFIG_FILE = config_file  # set once here, never to change again


@cli.group()
def create():
    """
    Creates a new Vagrant based SES cluster.

    It creates a deployment directory in <working_directory>/<deployment_id>
    with a Vagrantfile inside, and calls `vagrant up` to start the deployment.

    By default <working_directory> is located in `~/.sesdev`.

    Check all options available for a given command with:

    $ sesdev create <command> --help
    """


def _gen_settings_dict(
        version,
        apparmor=None,
        bluestore=None,
        ceph_branch=None,
        ceph_repo=None,
        ceph_salt_branch=None,
        ceph_salt_repo=None,
        cpus=None,
        deepsea_branch=None,
        deepsea_repo=None,
        deploy_ses=None,
        devel=None,
        disk_size=None,
        dry_run=None,
        domain=None,
        encrypted_osds=None,
        force=None,
        fqdn=None,
        image_path=None,  # kept for backwards compatibility
        ceph_image_path=None,
        grafana_image_path=None,
        prometheus_image_path=None,
        node_exporter_image_path=None,
        alertmanager_image_path=None,
        haproxy_image_path=None,
        keepalived_image_path=None,
        snmp_gateway_image_path=None,
        ipv6=None,
        libvirt_host=None,
        libvirt_networks=None,
        libvirt_private_key_file=None,
        libvirt_storage_pool=None,
        libvirt_user=None,
        non_interactive=None,
        num_disks=None,
        os=None,
        provision=None,
        qa_test_opt=None,
        ram=None,
        repo=None,
        repo_priority=None,
        rgw_ssl=None,
        roles=None,
        salt=None,
        scc_pass=None,
        scc_user=None,
        single_node=None,
        ssd=None,
        stop_before_ceph_orch_apply=None,
        stop_before_ceph_salt_apply=None,
        stop_before_cephadm_bootstrap=None,
        stop_before_ceph_salt_config=None,
        stop_before_deepsea_stage=None,
        stop_before_git_clone=None,
        stop_before_install_deps=None,
        stop_before_run_make_check=None,
        synced_folder=None,
        username=None,
        msgr2_secure_mode=None,
        msgr2_prefer_secure=None,
):

    settings_dict = {}

    if version == 'makecheck':
        settings_dict['roles'] = _parse_roles("[ makecheck ]")
    elif not single_node and roles:
        settings_dict['roles'] = _parse_roles(roles)
    elif single_node and roles:
        raise NoExplicitRolesWithSingleNode()
    elif single_node:
        roles_string = ""
        if version in ['ses7', 'ses7p']:
            roles_string = Constant.ROLES_SINGLE_NODE['ses7']
        elif version in ['octopus', 'pacific']:
            roles_string = Constant.ROLES_SINGLE_NODE['octopus']
        elif version in ['ses6', 'nautilus']:
            roles_string = Constant.ROLES_SINGLE_NODE['nautilus']
        elif version == 'caasp4':
            roles_string = Constant.ROLES_SINGLE_NODE['caasp4']
        else:
            raise VersionNotKnown(version)
        settings_dict['roles'] = _parse_roles(roles_string)

    if single_node is not None:
        settings_dict['single_node'] = single_node

    if os is not None:
        settings_dict['os'] = os

    if ipv6 is not None:
        settings_dict['ipv6'] = ipv6

    if cpus is not None:
        settings_dict['cpus'] = cpus
        settings_dict['explicit_cpus'] = True
    else:
        settings_dict['explicit_cpus'] = False

    if ram is not None:
        settings_dict['ram'] = ram
        settings_dict['explicit_ram'] = True
    else:
        settings_dict['explicit_ram'] = False

    if num_disks is not None:
        settings_dict['num_disks'] = num_disks
        settings_dict['explicit_num_disks'] = True
    else:
        settings_dict['explicit_num_disks'] = False

    if disk_size is not None:
        settings_dict['disk_size'] = disk_size

    if bluestore is not None:
        if bluestore:
            settings_dict['filestore_osds'] = False
        else:
            settings_dict['filestore_osds'] = True
            if not disk_size:
                # default 8 GB disk size is too small for FileStore
                settings_dict['disk_size'] = 15

    if libvirt_host is not None:
        settings_dict['libvirt_host'] = libvirt_host

    if libvirt_user is not None:
        settings_dict['libvirt_user'] = libvirt_user

    if libvirt_private_key_file is not None:
        settings_dict['libvirt_private_key_file'] = libvirt_private_key_file

    if libvirt_storage_pool is not None:
        settings_dict['libvirt_storage_pool'] = libvirt_storage_pool

    if libvirt_networks is not None:
        settings_dict['libvirt_networks'] = libvirt_networks

    if salt is not None:
        settings_dict['use_salt'] = salt

    if stop_before_deepsea_stage is not None:
        settings_dict['stop_before_stage'] = stop_before_deepsea_stage

    if deepsea_repo is not None:
        settings_dict['deepsea_git_repo'] = deepsea_repo

    if deepsea_branch is not None:
        settings_dict['deepsea_git_branch'] = deepsea_branch
        if not deepsea_repo:
            settings_dict['deepsea_git_repo'] = Constant.DEEPSEA_REPO

    if version is not None:
        settings_dict['version'] = version

    if provision is not None:
        settings_dict['provision'] = provision

    if repo_priority is not None:
        settings_dict['repo_priority'] = repo_priority

    if repo is not None:
        assert isinstance(repo, (list, tuple)), "repo is not a list or tuple"
        settings_dict['custom_repos'] = []
        count = 0
        # pylint: disable=invalid-name
        for repo_url in repo:
            count += 1
            settings_dict['custom_repos'].append(
                {
                    'name': 'custom-repo-{}'.format(count),
                    'url': _maybe_munge_repo_url(repo_url),
                    'priority': Constant.ZYPPER_PRIO_ELEVATED if repo_priority else None
                })

    if devel is not None:
        settings_dict['devel_repo'] = devel

    if qa_test_opt is not None:
        settings_dict['qa_test'] = qa_test_opt

    if scc_user is not None:
        settings_dict['scc_username'] = scc_user

    if scc_pass is not None:
        settings_dict['scc_password'] = scc_pass

    if domain is not None:
        settings_dict['domain'] = domain

    if non_interactive or force:
        settings_dict['non_interactive'] = True

    if dry_run is not None:
        settings_dict['dry_run'] = dry_run
        if dry_run:
            settings_dict['non_interactive'] = True

    if ssd is not None:
        settings_dict['ssd'] = ssd

    if fqdn is not None:
        settings_dict['fqdn'] = fqdn

    if encrypted_osds is not None:
        settings_dict['encrypted_osds'] = encrypted_osds

    if ceph_salt_repo is not None:
        if not ceph_salt_branch:
            Log.info(
                "User explicitly specified only --ceph-salt-repo; assuming --ceph-salt-branch {}"
                .format(Constant.CEPH_SALT_BRANCH)
            )
            ceph_salt_branch = Constant.CEPH_SALT_BRANCH

    if ceph_salt_branch is not None:
        if not ceph_salt_repo:
            Log.info(
                "User explicitly specified only --ceph-salt-branch; assuming --ceph-salt-repo {}"
                .format(Constant.CEPH_SALT_REPO)
            )
            ceph_salt_repo = Constant.CEPH_SALT_REPO

    if ceph_salt_repo:
        settings_dict['ceph_salt_git_repo'] = ceph_salt_repo

    if ceph_salt_branch:
        settings_dict['ceph_salt_git_branch'] = ceph_salt_branch

    if stop_before_ceph_salt_config is not None:
        settings_dict['stop_before_ceph_salt_config'] = stop_before_ceph_salt_config

    if stop_before_ceph_salt_apply is not None:
        settings_dict['stop_before_ceph_salt_apply'] = stop_before_ceph_salt_apply

    if stop_before_cephadm_bootstrap is not None:
        settings_dict['stop_before_cephadm_bootstrap'] = stop_before_cephadm_bootstrap

    if stop_before_ceph_orch_apply is not None:
        settings_dict['stop_before_ceph_orch_apply'] = stop_before_ceph_orch_apply

    if image_path is not None or ceph_image_path is not None:
        settings_dict['ceph_image_path'] = ceph_image_path or image_path
    if grafana_image_path is not None:
        settings_dict['grafana_image_path'] = grafana_image_path
    if node_exporter_image_path is not None:
        settings_dict['node_exporter_image_path'] = node_exporter_image_path
    if prometheus_image_path is not None:
        settings_dict['prometheus_image_path'] = prometheus_image_path
    if alertmanager_image_path is not None:
        settings_dict['alertmanager_image_path'] = alertmanager_image_path
    if keepalived_image_path is not None:
        settings_dict['keepalived_image_path'] = keepalived_image_path
    if haproxy_image_path is not None:
        settings_dict['haproxy_image_path'] = haproxy_image_path
    if snmp_gateway_image_path is not None:
        settings_dict['snmp_gateway_image_path'] = snmp_gateway_image_path

    if ceph_repo is not None:
        match = re.search(r'github\.com', ceph_repo)
        if match:
            settings_dict['makecheck_ceph_repo'] = ceph_repo
        else:
            settings_dict['makecheck_ceph_repo'] = 'https://github.com/{}/ceph'.format(ceph_repo)

    if ceph_branch is not None:
        settings_dict['makecheck_ceph_branch'] = ceph_branch

    if username is not None:
        settings_dict['makecheck_username'] = username

    if stop_before_git_clone is not None:
        settings_dict['makecheck_stop_before_git_clone'] = stop_before_git_clone

    if stop_before_install_deps is not None:
        settings_dict['makecheck_stop_before_install_deps'] = stop_before_install_deps

    if stop_before_run_make_check is not None:
        settings_dict['makecheck_stop_before_run_make_check'] = stop_before_run_make_check

    if deploy_ses:
        settings_dict['caasp_deploy_ses'] = True

    for folder in synced_folder:
        try:
            src, dst = folder.split(':')
            if path.isabs(src) and path.isabs(dst):
                pass
            else:
                raise OptionValueError(
                    "--synced-folder",
                    "Please provide absolute paths for synced folder paths",
                    folder
                    )
            if path.exists(src):
                pass
            else:
                raise OptionValueError(
                    "--synced-folder",
                    "Path to the source synced folder must exist",
                    src
                    )
        except ValueError as exc:
            raise OptionFormatError('--synced-folder', "src:dst", folder) from exc

    settings_dict['synced_folder'] = [folder.split(':') for folder in synced_folder]

    if msgr2_secure_mode:
        settings_dict['msgr2_secure_mode'] = True
    if msgr2_prefer_secure:
        settings_dict['msgr2_prefer_secure'] = True

    if apparmor is not None:
        settings_dict['apparmor'] = apparmor

    if rgw_ssl is not None:
        if rgw_ssl and version not in ['nautilus', 'ses6']:
            raise OptionNotSupportedInVersion('--rgw-ssl', version)
        settings_dict['rgw_ssl'] = rgw_ssl

    return settings_dict


def _create_command(deployment_id, settings_dict):
    interactive = not settings_dict.get('non_interactive', False)
    Log.debug("_create_command: interactive set to {}".format(interactive))
    settings = Settings(**settings_dict)
    dep = Deployment.create(deployment_id, _print_log, settings)
    if not dep.settings.devel_repo:
        if dep.settings.version not in Constant.CORE_VERSIONS:
            raise OptionNotSupportedInVersion('--product', dep.settings.version)
    really_want_to = None
    click.echo("=== Creating deployment \"{}\" with the following configuration ==="
               .format(deployment_id)
               )
    click.echo(dep.configuration_report(show_individual_vms=(not interactive)))
    really_want_to = True
    if interactive:
        not_sure = True
        details_already_shown = False
        while not_sure:
            if details_already_shown:
                really_want_to = click.prompt(
                    ('Proceed with deployment (y=yes, n=no, b=show basic config again, '
                     'd=show details again) ?'),
                    type=str,
                    default="y",
                )
            else:
                really_want_to = click.prompt(
                    'Proceed with deployment (y=yes, n=no, d=show details) ?',
                    type=str,
                    default="y",
                )
            really_want_to = really_want_to.lower()[0]
            # pylint: disable=consider-using-in
            if really_want_to == 'y' or not really_want_to:
                really_want_to = True
                break
            if really_want_to == 'n':
                really_want_to = False
                break
            if really_want_to == 'b':
                click.echo(dep.configuration_report(
                    show_deployment_wide_params=True,
                    show_individual_vms=False,
                ))
            if really_want_to == 'd':
                details_already_shown = True
                click.echo(dep.configuration_report(
                    show_deployment_wide_params=False,
                    show_individual_vms=True,
                ))
    try:
        if really_want_to:
            dep.vet_configuration()
            if dep.settings.dry_run:
                click.echo("Dry run. Stopping now, before creating any VMs.")
                raise click.Abort()
            dep.start(_print_log)
            dep.user_provision()
            click.echo("=== Deployment Finished ===")
            click.echo()
            click.echo("You can login into the cluster with:")
            click.echo()
            click.echo("  $ sesdev ssh {}".format(deployment_id))
            click.echo()
            if dep.settings.version == 'octopus' and dep.has_suma():
                click.echo("Or, access the SUMA WebUI with:")
                click.echo()
                click.echo("  $ sesdev tunnel {} suma".format(deployment_id))
                click.echo()
            else:
                click.echo("Or, access the Ceph Dashboard with:")
                click.echo()
                click.echo("  $ sesdev tunnel {} dashboard".format(deployment_id))
                click.echo()
        else:
            raise click.Abort()
    except click.Abort:
        click.echo()
        click.echo("Exiting...")
        dep.destroy(_silent_log)


def _prep_kwargs(kwargs):
    # Click 6 and Click 7 have different option-naming semantics
    # for options with aliases
    # handle them both
    if 'non_interactive' in kwargs and kwargs['non_interactive'] is not None:
        kwargs['force'] = kwargs['non_interactive']
    elif 'force' in kwargs and kwargs['force'] is not None:
        kwargs['non_interactive'] = kwargs['force']


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@libvirt_options
def ses6(deployment_id, **kwargs):
    """
    Creates a SES6 cluster using SLES-15-SP1
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('ses6', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses6', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def ses7(deployment_id, **kwargs):
    """
    Creates a SES7 Octopus cluster using SLES-15-SP2 and packages (and container image)
    from the Devel:Storage:7.0 IBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('ses7', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses7', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def ses7p(deployment_id, **kwargs):
    """
    Creates a SES7 Pacific cluster using SLES-15-SP3 and packages (and container image)
    from the Devel:Storage:7.0:Pacific IBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('ses7p', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses7p', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@libvirt_options
def nautilus(deployment_id, **kwargs):
    """
    Creates a Ceph Nautilus cluster using openSUSE Leap 15.1 and packages
    from filesystems:ceph:nautilus OBS project
    """
    _prep_kwargs(kwargs)
    if not kwargs['devel']:
        # nautilus requires devel repo for deepsea
        raise OptionNotSupportedInVersion('--product', 'nautilus')
    settings_dict = _gen_settings_dict('nautilus', **kwargs)
    deployment_id = _maybe_gen_dep_id('nautilus', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def octopus(deployment_id, **kwargs):
    """
    Creates a Ceph Octopus cluster using openSUSE Leap 15.2 and packages
    (and container image) from filesystems:ceph:octopus:upstream OBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('octopus', **kwargs)
    deployment_id = _maybe_gen_dep_id('octopus', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def pacific(deployment_id, **kwargs):
    """
    Creates a Ceph Pacific cluster using openSUSE Leap 15.2 and packages
    (and container image) from filesystems:ceph:master:upstream OBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('pacific', **kwargs)
    deployment_id = _maybe_gen_dep_id('pacific', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@libvirt_options
@click.option("--deploy-ses", is_flag=True, default=False,
              help="Deploy SES using rook in CaasP")
def caasp4(deployment_id, **kwargs):
    """
    Creates a CaaSP cluster using SLES 15 SP2
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('caasp4', **kwargs)
    deployment_id = _maybe_gen_dep_id('caasp4', deployment_id, settings_dict)
    _create_command(deployment_id, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@libvirt_options
@click.option("--ceph-repo", default=None,
              help='repo from which to clone Ceph source code')
@click.option("--ceph-branch", default=None,
              help='ceph branch on which to run "make check"')
@click.option("--username", default='sesdev',
              help='name of ordinary user that will run make check')
@click.option("--stop-before-git-clone", is_flag=True, default=False,
              help="Stop before cloning the git repo")
@click.option("--stop-before-install-deps", is_flag=True, default=False,
              help="Stop before running install-deps.sh")
@click.option("--stop-before-run-make-check", is_flag=True, default=False,
              help="Stop before running run-make-check.sh")
def makecheck(deployment_id, **kwargs):
    """
    Brings up a single VM and clones a Ceph repo/branch which can either be
    specified explicitly on the command line or, failing that, will default to
    something reasonable depending on which OS is specified. Inside the Ceph
    clone, first "install-deps.sh" and then "run-make-check.sh" will be run.
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('makecheck', **kwargs)
    if not deployment_id:
        os = settings_dict['os'] if 'os' in settings_dict else 'tumbleweed'
        safe_os = os.replace('_', '-').replace('.', '-')
        deployment_id = 'makecheck-{}'.format(safe_os)
    _create_command(deployment_id, settings_dict)


def _maybe_glob_deps(deployment_id):
    matching_deployments = None
    if tools.is_a_glob(deployment_id):
        deps = Deployment.list(True)
        dep_ids = [d.dep_id for d in deps]
        matching_dep_ids = fnmatch.filter(dep_ids, deployment_id)
        matching_deployments = [d for d in deps if d.dep_id in matching_dep_ids]
    else:
        matching_deployments = [Deployment.load(deployment_id)]
    return matching_deployments


def _cluster_singular_or_plural(an_iterable):
    if len(an_iterable) == 1:
        return "cluster"
    return "clusters"


@cli.command(name='add-repo')
@click.option('--repo-priority/--no-repo-priority', default=False,
              help="Set elevated priority on custom zypper repos")
@click.option('--update/--no-update', is_flag=True,
              help='Update packages after adding devel repo')
@click.argument('deployment_id')
@click.argument('custom_repo', required=False)
def add_repo(deployment_id, **kwargs):
    """
    Add a custom repo to all nodes of an already-deployed cluster. The repo
    should be specified in the form of an URL, but it is optional: if it is
    omitted, the "devel" repo (which has a specific meaning depending on the
    deployment version) will be added.
    """
    if kwargs['update'] and kwargs['custom_repo']:
        raise AddRepoNoUpdateWithExplicitRepo()
    dep = Deployment.load(deployment_id)
    custom_repo = None
    if kwargs['custom_repo']:
        custom_repo = ZypperRepo(
            name='custom_repo_{}'.format(tools.gen_random_string(6)),
            url=_maybe_munge_repo_url(kwargs['custom_repo']),
            priority=Constant.ZYPPER_PRIO_ELEVATED if kwargs['repo_priority'] else None
        )
    dep.add_repo_subcommand(custom_repo, kwargs['update'], _print_log)


@cli.group()
def box():
    """
    Commands to manipulate Vagrant Boxes
    """


@box.command(name='list')
@click.argument('box_name', required=False)
@libvirt_options
def list_boxes(box_name, **kwargs):
    """
    List Vagrant Boxes installed in the system.

    When no argument is provided, lists all boxes. The optional argument can be
    either a literal box name, a box alias, or a glob (globs match against
    literal box names, only).
    """
    box_list_handler(box_name, **kwargs)


@box.command(name='remove')
@click.argument('box_name')
@libvirt_options
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              help='Allow to remove Vagrant Box(es) without user confirmation',
             )
def remove_box(box_name, **kwargs):
    """
    Remove one or more Vagrant Boxes that were installed in the system by sesdev.

    Takes one mandatory argument, which can be either a literal box name, a box
    alias, or a glob (globs match against literal box names, only).
    """
    box_remove_handler(box_name, **kwargs)


@cli.command()
@click.argument('deployment_id')
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              default=False,
              help='Allow to destroy the deployment without user confirmation',
              )
@click.option('--destroy-networks', is_flag=True, default=False,
              help='Allow to destroy networks associated with the deployment')
def destroy(deployment_id, **kwargs):
    """
    Destroys the deployment(s) named DEPLOYMENT_SPEC -- where DEPLOYMENT_SPEC might
    be either a literal deployment ID or a glob ("octopus_*") -- by destroying the
    VMs and deleting the deployment directory.
    """
    interactive = not (kwargs.get('non_interactive', False) or kwargs.get('force', False))
    destroy_networks = kwargs.get('destroy_networks', False)
    matching_deployments = _maybe_glob_deps(deployment_id)
    cluster_word = _cluster_singular_or_plural(matching_deployments)
    if interactive:
        really_want_to = click.confirm(
            'Do you really want to destroy {} {}'.format(len(matching_deployments), cluster_word),
            default=True,
        )
        if not really_want_to:
            raise click.Abort()
    for dep in matching_deployments:
        Log.debug("destroy deployment: '{}', destroy networks: {}"
                  .format(deployment_id, destroy_networks))
        dep.destroy(_print_log, destroy_networks)
        click.echo("Deployment {} destroyed!".format(dep.dep_id))


def _link_load_deployment(dep_id):
    click.echo("Loading deployment {}".format(dep_id))
    dep = Deployment.load(dep_id)
    dep_ssh_public_key = dep.sync_ssh("master",
                                      ["cat", "~/.ssh/id_rsa.pub"]
                                     ).rstrip()
    Log.info("Deployment {} SSH public key: {}"
             .format(dep_id, dep_ssh_public_key)
            )
    return (dep, dep_ssh_public_key)


def _link_populate_files(dep_1, dep_2, dep_2_ssh_public_key):
    click.echo()
    for (dep_1_node_name, _) in dep_1.nodes.items():
        click.echo("=> populating /etc/hosts and ~/.ssh/authorized_keys on "
                   "node \"{}\" of deployment \"{}\""
                   .format(dep_1_node_name, dep_1.dep_id)
                  )
        for (_, dep_2_node_obj) in dep_2.nodes.items():
            dep_1.ssh(dep_1_node_name,
                      ["echo {} {} >> /etc/hosts ; echo {} >> ~/.ssh/authorized_keys"
                       .format(dep_2_node_obj.public_address,
                               dep_2_node_obj.fqdn,
                               dep_2_ssh_public_key
                              )
                      ],
                     )


@cli.command(name='link')
@click.argument('dep_id_1')
@click.argument('dep_id_2')
def link(dep_id_1, dep_id_2):
    """
    Link two clusters together (EXPERIMENTAL)

    See README.md for more information on using this feature.
    """
    (dep_1, dep_1_ssh_public_key) = _link_load_deployment(dep_id_1)
    (dep_2, dep_2_ssh_public_key) = _link_load_deployment(dep_id_2)
    _link_populate_files(dep_1, dep_2, dep_2_ssh_public_key)
    _link_populate_files(dep_2, dep_1, dep_1_ssh_public_key)
    click.echo()
    click.echo("Before you will be able to send network packets from one deployment to")
    click.echo("the other, the obstacles preventing such communication must be removed.")
    click.echo("This can be accomplished by issuing the following two commands, as root,")
    click.echo("on the libvirt host:")
    click.echo()
    click.echo("# iptables -F LIBVIRT_FWI")
    click.echo("# iptables -A LIBVIRT_FWI -j ACCEPT")
    click.echo()
    click.echo("Have a nice day!")


@click.option('--format', 'format_opt', type=str, default=None,
              help="Provide --format=json for JSON output")
@cli.command(name='list')
def list_deps(**kwargs):
    """
    (DEPRECATED) replaced by 'sesdev status'
    """
    format_opt = kwargs.get('format_opt', None)
    if format_opt in ['json']:
        Log.warning("Deprecated \"sesdev list\" was called with --format option")
    else:
        click.echo()
        click.echo("***************************************")
        click.echo("DEPRECATED: USE \"sesdev status\" instead!")
        click.echo("***************************************")
        click.echo()
    _show_status_of_all_deployments(**kwargs)


@cli.command(name='qa-test')
@click.argument('deployment_id')
def qa_test(deployment_id):
    """
    Runs QA test on an already-deployed cluster.
    """
    dep = Deployment.load(deployment_id)
    dep.qa_test(_print_log)


@cli.command()
@click.argument('deployment_id')
@click.argument('node')
def reboot(deployment_id, node):
    dep = Deployment.load(deployment_id)
    dep.reboot_one_node(_print_log, node)


@cli.command()
@click.argument('deployment_id')
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              callback=_abort_if_false,
              default=False,
              expose_value=False,
              help='Allow to redeploy the cluster without user confirmation',
              prompt='Are you sure you want to redeploy the cluster?')
def redeploy(deployment_id, **kwargs):
    """
    Destroys the VMs of the deployment DEPLOYMENT_ID and deploys again the cluster
    from scratch with the same configuration.
    """
    interactive = not (kwargs.get('non_interactive', False) or kwargs.get('force', False))
    if interactive:
        really_want_to = True
        if interactive:
            really_want_to = click.confirm(
                'Do you want to continue with the deployment?',
                default=True,
            )
        if not really_want_to:
            raise click.Abort()
    dep = Deployment.load(deployment_id)
    dep.destroy(_print_log)
    dep = Deployment.create(deployment_id, _print_log, dep.settings)
    dep.start(_print_log)


@cli.command(name='replace-ceph-salt')
@click.argument('deployment_id')
@click.option('--local', default=None, type=str, show_default=True,
              help='The local path for "ceph-salt" source')
def replace_ceph_salt(deployment_id, local=None):
    """
    Install ceph-salt from source
    """
    dep = Deployment.load(deployment_id)
    dep.replace_ceph_salt(local)


@cli.command(name='replace-mgr-modules')
@click.argument('deployment_id')
@click.option('--local', type=str, help='The local repository path. E.g.: ~/ceph')
@click.option('--pr', type=int, help='The PR to be fetched from a remote repository')
@click.option('--branch', default='master', type=str, show_default=True,
              help='The branch to be fetched from a remote repository')
@click.option('--repo', default='ceph', type=str, show_default=True,
              help='The remote repository from which to fetch PRs or branches')
@click.option('--langs', default='en-US', type=str, show_default=True,
              help='Dashboard languages to be built')
def replace_mgr_modules(deployment_id, **kwargs):
    """
    Fetches a different version of Ceph MGR modules from a local repository or github,
    replacing the installed ones.

    --local, --pr and --branch conflict with each other,
    when the first is found the remaining are ignored.
    """
    dep = Deployment.load(deployment_id)
    dep.replace_mgr_modules(**kwargs)


@cli.command()
@click.option('--recursive/--no-recursive', '-r/ ', is_flag=True,
              help='Pass -r to scp')
@click.argument('deployment_id')
@click.argument('source')
@click.argument('destination')
def scp(recursive, deployment_id, source, destination):
    """
    Prepares and executes a 'scp' command to copy a file or entire directory
    from a cluster node to the host, or from the host to a cluster node.

    Takes three arguments: in addition to deployment_id, it needs both a source
    and destination, one of which will be in a special form:

        <node>:<path>

    Note: You can check the existing node names with the command
    "sesdev show <deployment_id>"

    For example, to copy the file /etc/os-release from the node 'master'
    on cluster (deployment_id) 'foo' to the current directory on the host:

        sesdev scp foo master:/etc/os-release .

    To recursively copy the entire directory "/bar" from the host to "/root/bar"
    on node1 in deployment foo:

        sesdev scp --recursive foo /bar node1:

    (From the cluster node's perspective, the scp operation will be done as
    root.)

    The --recursive option can also be abbreviated to -r and can appear anywhere
    in the command line, e.g.:

        sesdev scp foo -r /bar node1:
    """
    dep = Deployment.load(deployment_id)
    dep.scp(source, destination, recurse=recursive)


@cli.command()
@click.option('--detail/--no-detail', is_flag=True, default=False,
              help='Display details of each VM in additional to deployment-wide configuration')
@click.option('--format', 'format_opt', type=str, default=None,
              help="Provide --format=json for JSON output")
@click.option('--nodes-with-role', default=None, type=str,
              help='Display details of each VM in additional to deployment-wide configuration')
@click.argument('deployment_id')
def show(deployment_id, **kwargs):
    """
    Display the configuration of a running deployment - this is the same
    information that is displayed by the "create" command before asking the user
    whether they are really sure they want to create the cluster). Use "--detail"
    to get information on individual VMs in the deployment.
    """
    format_opt = kwargs.get('format_opt', None)
    nodes_with_role_option = kwargs.get('nodes_with_role', None)
    if nodes_with_role_option:
        role_in_question = nodes_with_role_option
        if not role_in_question:
            raise YouMustProvide("a role")
    dep = Deployment.load(deployment_id)
    if nodes_with_role_option:
        if format_opt in ['json']:
            retval = dep.nodes_with_role.get(role_in_question, [])
            click.echo(json.dumps(retval, sort_keys=True, indent=4))
        else:
            if role_in_question in dep.nodes_with_role:
                multiple_nodes = len(dep.nodes_with_role[role_in_question]) > 1
                retval = ",".join(dep.nodes_with_role[role_in_question])
                if multiple_nodes:
                    click.echo("In deployment '{}', nodes {} have role '{}'"
                               .format(dep.dep_id, retval, role_in_question)
                              )
                else:
                    click.echo("In deployment '{}', node {} has role '{}'"
                               .format(dep.dep_id, retval, role_in_question)
                              )
            else:
                raise NoNodeWithRole(dep.dep_id, role_in_question)
    else:
        if format_opt in ['json']:
            raise OptionNotSupportedInContext('--format=json')
        click.echo(dep.configuration_report(show_individual_vms=kwargs['detail']))


@cli.command()
@click.argument('deployment_id')
def report(deployment_id):
    """
    Compile the relevant information for the maintenance test report. This
    includes cluster-wide information, individual VM information and package
    installation statuses.
    """
    def _indent(string, spaces=4):
        return " " * spaces + string

    dep = Deployment.load(deployment_id)
    ver = Constant.VERSION_OFFICIAL[dep.settings.version]
    cmd = f"sesdev create {dep.settings.version} --product --repo-priority"
    for rep in dep.settings.custom_repos:
        cmd += " --repo {}".format(rep['url'])
    cmd += f" {deployment_id}"
    dep.start(_print_log)

    repos = dep.list_repos()
    packages = dep.list_packages(repos=[r['url'] for r in dep.settings.custom_repos])

    click.echo("<QAM-SES>")
    click.echo("")
    click.echo("* sesdev was used for installation/smoke testing")
    click.echo("")
    click.echo(f"* Command for creating a {ver} test cluster:")
    click.echo(_indent(cmd))
    click.echo("")
    click.echo(f"* {ver} cluster characteristics:")
    for line in dep.configuration_report(show_individual_vms=True).splitlines():
        click.echo(_indent(line))
    click.echo("")

    click.echo("* List of repos configured:")
    for node, repos in repos.items():
        click.echo("")
        click.echo(f" -- {node}:")
        for repo in repos:
            click.echo(_indent(f"{repo.name:20} {repo.priority:3} {repo.url}"))
    click.echo("")

    click.echo("* Packages installed from Maintenance repos:")
    for node, pkgs in packages.items():
        click.echo("")
        click.echo(f" -- {node}:")
        for pkg in pkgs:
            click.echo(_indent(f"{pkg.name}  {pkg.version}  (from {pkg.repo})"))
    click.echo("")

    click.echo("* Ceph versions:")
    click.echo("")
    versions = dep.list_versions()
    click.echo(_indent("service type | count | version"))
    for service_name in versions.keys():
        service_name_is_already_printed = False
        for service_version, service_count in versions[service_name].items():
            if service_name_is_already_printed:
                click.echo(_indent(f"             | {service_count:5} | {service_version}"))
            else:
                click.echo(_indent(f"{service_name:12} | {service_count:5} | {service_version}"))
                service_name_is_already_printed = True
    click.echo("")

    click.echo(f"* {ver} cluster status:")
    click.echo("")
    dep.ssh('master', ['ceph', 'status'], interactive=False)
    click.echo("")
    click.echo("* Workflow QAM-SES: PASSED/FAILED")
    click.echo("</QAM-SES>")


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
@click.argument('command', required=False, nargs=-1, type=click.Path())
def ssh(deployment_id, node=None, command=None):
    """
    Opens an SSH shell to, or runs optional COMMAND on, node NODE in deployment
    DEPLOYMENT_ID.

    If the node is not specified, it defaults to "master".

    Note: You can check the existing node names with the command
    "sesdev show <deployment_id>"
    """
    dep = Deployment.load(deployment_id)
    node_name = 'master' if node is None else node

    cmd = ' '.join(['\"' + s + '\"' if " " in s else s for s in list(command)])
    if cmd:
        Log.info("Running SSH command on {}: {}".format(node_name, cmd))
        retval = dep.ssh(node_name, [cmd], interactive=False)
    else:
        retval = dep.ssh(node_name, [cmd], interactive=True)

    assert isinstance(retval, int), "ssh method returned non-integer"
    if retval != 0:
        raise SSHCommandReturnedNonZero(retval)


@cli.command()
@click.option('--format', 'format_opt', type=str, default=None,
              help="Provide --format=json for JSON output")
@click.argument('deployment_id', required=False)
@click.argument('node', required=False)
def status(**kwargs):
    """
    Without any arguments, lists all deployments and their current status.
    When called with a deployment ID, lists the individual nodes of that
    deployment, and their current status. When called with a deployment ID
    and a node, displays the status of just that node.
    """
    deployment_id = kwargs.get('deployment_id')
    node_opt = kwargs.get('node')
    format_opt = kwargs.get('format_opt')
    node_list = []
    if deployment_id:
        dep = Deployment.load(deployment_id)
        node_found = False
        if format_opt not in ['json']:
            p_table = PrettyTable(["Node", "Status", "Public Address",
                                   "Cluster Address"])
            p_table.align = "l"
        for (node_name, node_obj) in dep.nodes.items():
            if node_opt:
                if node_name == node_opt:
                    node_found = True
                    if format_opt in ['json']:
                        click.echo("\"{}\"".format(node_obj.status))
                        return
                    p_table.add_row([node_name, node_obj.status,
                                     node_obj.public_address,
                                     node_obj.cluster_address])
            else:
                if format_opt in ['json']:
                    node_list.append({
                        "name": node_name,
                        "status": node_obj.status,
                        "public_address": node_obj.public_address,
                        "cluster_address": node_obj.cluster_address,
                    })
                else:
                    p_table.add_row([node_name, node_obj.status,
                                     node_obj.public_address,
                                     node_obj.cluster_address])
        if node_opt:
            if node_found:
                assert format_opt not in ['json'], \
                    (
                        "BADNESS: this code block should not have been reached. Report it "
                        "as a bug! Bailing out!"
                    )
                click.echo()
                click.echo("Current status of node \"{}\" in deployment \"{}\""
                           .format(node_opt, deployment_id)
                          )
                click.echo()
                click.echo(p_table)
                click.echo()
            else:
                raise NodeDoesNotExist(node_opt, deployment_id)
        else:
            if format_opt in ['json']:
                click.echo(json.dumps(node_list, sort_keys=True, indent=4))
            else:
                click.echo()
                click.echo("Current status of the {} nodes of deployment \"{}\""
                           .format(len(dep.nodes), deployment_id)
                          )
                click.echo()
                click.echo(p_table)
                click.echo()
    else:
        # bare "sesdev status" is synonymous with "sesdev list"
        _show_status_of_all_deployments(format_opt=format_opt)


def _show_status_of_all_deployments(**kwargs):
    format_opt = kwargs.get('format_opt')
    p_table = None
    deployments_list = []
    deps = Deployment.list(True)
    if deps:
        Log.info("list_deps: Found deployments: {}".format(", ".join(d.dep_id for d in deps)))
    else:
        msg = "No deployments found"
        Log.info("list_deps: {}".format(msg))
        if format_opt in ['json']:
            click.echo(json.dumps([], sort_keys=True, indent=4))
        else:
            click.echo(msg)
        return None

    def _status(nodes):
        status_str = None
        for node in nodes.values():
            if status_str is None:
                status_str = node.status
            elif node.status == 'running' and status_str == 'not deployed':
                status_str = 'partially deployed'
            elif node.status == 'stopped' and status_str == 'running':
                status_str = 'partially running'
            elif node.status == 'suspended' and status_str == 'running':
                status_str = 'partially running'
            elif node.status == 'running' and status_str == 'stopped':
                status_str = 'partially running'
            elif node.status == 'running' and status_str == 'suspended':
                status_str = 'partially running'
        return status_str

    if format_opt not in ['json']:
        p_table = PrettyTable(["ID", "Version", "Status", "Nodes",
                               "Public Network", "Cluster Network"])
        p_table.align = "l"

    for dep in deps:
        Log.debug("_status: Looping over deployments ({})".format(dep.dep_id))
        status_str = str(_status(dep.nodes))
        Log.debug("_status: -> status: {}".format(status_str))
        version = getattr(dep.settings, 'version', None)
        Log.debug("_status: -> version: {}".format(version))
        nodes = getattr(dep, 'nodes', None)
        node_names = '(unknown)' if nodes is None else ', '.join(nodes)
        Log.debug("_status: -> node_names: {}".format(node_names))
        public_network = getattr(dep, 'public_network_segment', None)
        Log.debug("_status: -> public_network: {}".format(public_network))
        cluster_network = getattr(dep, 'cluster_network_segment', None)
        Log.debug("_status: -> public_network: {}".format(public_network))
        if format_opt in ['json']:
            deployments_list.append({
                "id": dep.dep_id,
                "version": version,
                "status": status_str,
                "nodes": list(nodes),
                "public_network:": public_network,
                "cluster_network:": cluster_network,
            })
        else:
            p_table.add_row([dep.dep_id, version, status_str, node_names,
                             public_network, cluster_network])
    if format_opt in ['json']:
        click.echo(json.dumps(deployments_list, sort_keys=True, indent=4))
    else:
        deployment_word = "deployments" if len(deps) > 1 else "deployment"
        click.echo("Found {} {}:".format(len(deps), deployment_word))
        click.echo()
        click.echo(p_table)
        click.echo()


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def start(deployment_id, node=None):
    """
    Starts the VMs of the deployment DEPLOYMENT_SPEC, where DEPLOYMENT_SPEC
    might be either a literal deployment ID or a glob ("octopus_*").

    If cluster was not yet deployed (if was created with the --no-deploy flag), it will
    start the deployment of the cluster.
    """
    matching_deployments = _maybe_glob_deps(deployment_id)
    click.echo("Starting {} {}".format(
        len(matching_deployments),
        _cluster_singular_or_plural(matching_deployments),
    ))
    if len(matching_deployments) > 1 and node:
        click.echo("Ignoring node advice because DEPLOYMENT_SPEC is a glob")
        node = None
    for dep in matching_deployments:
        dep.start(_print_log, node=node)
        click.echo("Deployment {} started!".format(dep.dep_id))


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def stop(deployment_id, node=None):
    """
    Stops the VMs of the deployment DEPLOYMENT_SPEC, where DEPLOYMENT_SPEC
    might be either a literal deployment ID or a glob ("octopus_*").
    """
    matching_deployments = _maybe_glob_deps(deployment_id)
    click.echo("Stopping {} {}".format(
        len(matching_deployments),
        _cluster_singular_or_plural(matching_deployments),
    ))
    if len(matching_deployments) > 1 and node:
        click.echo("Ignoring node advice because DEPLOYMENT_SPEC is a glob")
        node = None
    for dep in matching_deployments:
        dep.stop(_print_log, node)
        click.echo("Deployment {} stopped!".format(dep.dep_id))


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def supportconfig(deployment_id, node):
    """
    Runs supportconfig on a node within an already-deployed cluster. Dumps the
    resulting tarball in the current working directory.

    If the node is not specified, it defaults to "master".

    NOTE: supportconfig is only available in deployments running on SUSE Linux
    Enterprise.
    """
    dep = Deployment.load(deployment_id)
    _node = 'master' if node is None else node
    dep.supportconfig(_print_log, _node)


@cli.command()
@click.argument('deployment_id')
@click.argument('service', type=click.Choice(['dashboard', 'grafana', 'suma',
                                              'prometheus', 'alertmanager']), required=False)
@click.option('--node', default='master', type=str, show_default=True,
              help='The node where we want to create the tunnel to')
@click.option('--remote-port', default=None, type=int,
              help='The service port in the remote machine')
@click.option('--local-port', default=None, type=int, help='The local port for the tunnel')
@click.option('--local-address', default='localhost', type=str, show_default=True,
              help='The local address to bind the tunnel')
def tunnel(deployment_id, service=None, node=None, remote_port=None, local_port=None,
           local_address=None):
    """
    Creates an SSH port forwarding for the services that are running in the
    deployment DEPLOYMENT_ID.

    If SERVICE is not specified, you can use the --remote-port and --node to forward
    a generic service.
    """
    dep = Deployment.load(deployment_id)
    if service:
        if service == 'dashboard':
            click.echo("Opening tunnel to service 'dashboard' in deployment '{}'..."
                       .format(dep.dep_id))
        else:
            click.echo("Opening tunnel to service '{}' on node '{}' of "
                       "deployment '{}'..."
                       .format(service, node, dep.dep_id))
    elif remote_port:
        click.echo("Opening tunnel between remote {} port and local {} port on "
                   "node '{}' of deployment '{}'..."
                   .format(
                       remote_port,
                       local_port if local_port else remote_port,
                       node,
                       dep.dep_id)
                   )
    dep.start_port_forwarding(service, node, remote_port, local_port, local_address)


@cli.command()
@click.argument('deployment_id')
@click.argument('node')
@click.option('--devel/--product', 'devel_repos', default=True, is_flag=True,
              help="Upgrade to devel or product repos (default: devel)")
@click.option('--to', 'to_version', default='octopus', type=str, show_default=True,
              help='The local address to bind the tunnel')
def upgrade(deployment_id, node, devel_repos, to_version):
    """
    What will happen when I issue this command on a node?
    - old repositories will be wiped out
    - new repositories will be added
    - zypper dup
    - reboot
    """
    dep = Deployment.load(deployment_id)
    dep.upgrade(_print_log, node, devel_repos, to_version)


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def user_provision(deployment_id, node):
    dep = Deployment.load(deployment_id)
    dep.user_provision(node)


@cli.command()
@click.argument('shell', type=click.Choice(['bash', 'zsh', 'fish']), required=True)
def shell_completion(shell):
    """
    Generate shell completion code
    """
    environ['_SESDEV_COMPLETE'] = shell + '_source'
    completion = tools.run_sync('sesdev')
    print(completion)
    environ['_SESDEV_COMPLETE'] = ''


@cli.command()
@click.argument('review_request_id')
@click.argument('version')
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def maintenance_test(review_request_id, version, **kwargs):
    """
    Create a test cluster for installation/smoke testing of package maintenance
    updates. Takes a review request id of the form 'SUSE:Maintenance:xxxxx:yyyyyy'
    or 'S:M:xxxxx:yyyyyy' and a SES version and creates a test cluster.

    The difference between the test cluster and a 'normal' sesdev cluster is
    that the test cluster has exra repositories from which it installs the
    packages under testing.

    This function basically hard-codes

        sesdev create {version} --product --repo-priority \
          --repo http://download.suse.de/ibs/SUSE:/Maintenance:/xxxxx/SUSE_SLE-15_Update \
          --repo \
          http://download.suse.de/ibs/SUSE:/Maintenance:/xxxxx/SUSE_Updates_Storage_{vnum}_x86_64 \
          {xxxxx}-{yyyyy}-{version}
    """
    def _check_url(url):
        try:
            get = requests.get(url)

            if get.status_code == 200:
                return True
            return False
        except requests.exceptions.RequestException:
            return False

    def _parse_review_request_id(rrid):
        """
        Takes a Review Request ID of the form S:M:xxxxx:yyyyyy or
        SUSE:Maintenance:xxxxx:yyyyyy as a string and returns just the
        maintenance incident id and the review reuqest number as a pair of
        strings. If the given argument does not sufficiently conform to the
        format of a Review Request ID, a ValueError with a descriptive message
        is raised.

        Example input:

            "SUSE:Maintenance:12345:678901"

        Example output:

            ("12345", "678901")
        """
        try:
            suse, maintenance, maintenance_incident, review_request = rrid.split(':')
            if suse not in ['SUSE', 'S']:
                raise ValueError("Not a Review Request ID. Must begin with `SUSE:` or `S:`")
            if maintenance not in ['Maintenance', 'M']:
                raise ValueError("Not a Review Request ID. Second part must be"
                                 " `Maintenance:` or `M:`")
            if 0 > int(maintenance_incident) or 100000 < int(maintenance_incident):
                raise ValueError("Not a Review Request ID. The Maintenance"
                                 " Incident ID must be a positive five digit number.")
            if 0 > int(review_request) or 1000000 < int(review_request):
                raise ValueError("Not a Review Request ID. The Review Request Number"
                                 " must be a positive six digit number.")

            if not _check_url(f"http://qam2.suse.de/reports/SUSE:Maintenance:\
{maintenance_incident}:{review_request}"):
                raise ValueError(f"Not a valid Review Request ID. The Review Request ID \
'SUSE:Maintenance:{maintenance_incident}:{review_request}' \
does not exist.")
            return (maintenance_incident, review_request)
        except ValueError as value_error:
            click.echo(f"{value_error}")
            click.echo(f"Review Request ID {rrid} does not conform to pattern S:M:xxxxx:yyyyyy")
            sys.exit(1)

    maintenance_incident_id, review_request_number = _parse_review_request_id(review_request_id)
    deployment_id = f"{maintenance_incident_id}-{review_request_number}-{version}"

    repo_urls = {}

    for alias, url in Constant.MAINTENANCE_REPO_TEMPLATES[version].items():
        if _check_url(url.format(maintenance_incident_id)):
            repo_urls[alias.format(maintenance_incident_id)] = url.format(maintenance_incident_id)

    if len(repo_urls) == 0:
        click.echo('Could not find any maintenance repos.')
        click.echo('Please make sure you are connected to the E&I VPN.')
        click.echo('\nThe following URLs were probed:')
        for alias, url in Constant.MAINTENANCE_REPO_TEMPLATES[version].items():
            click.echo('  - ' + alias.format(maintenance_incident_id) + ': ' +
                       url.format(maintenance_incident_id))
        click.echo('Aborting...')
        sys.exit(1)

    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict(version, **kwargs)
    settings_dict['devel_repo'] = False
    settings_dict['repo_priority'] = True

    for repo_name, repo_url in repo_urls.items():
        settings_dict['custom_repos'].append(
            {
                'name': repo_name,
                'url': _maybe_munge_repo_url(repo_url),
                'priority': Constant.ZYPPER_PRIO_ELEVATED
            })

    _create_command(deployment_id, settings_dict)
