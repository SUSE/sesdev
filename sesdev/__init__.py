import fnmatch
import json
import logging
from os import environ, path
import re
import sys

from prettytable import PrettyTable

import click
import pkg_resources

from seslib.box import Box
from seslib.constant import Constant
from seslib.deployment import Deployment
from seslib.exceptions import \
                              SesDevException, \
                              AddRepoNoUpdateWithExplicitRepo, \
                              BoxDoesNotExist, \
                              CmdException, \
                              DebugWithoutLogFileDoesNothing, \
                              NoExplicitRolesWithSingleNode, \
                              OptionFormatError, \
                              OptionNotSupportedInVersion, \
                              OptionValueError, \
                              RemoveBoxNeedsBoxNameOrAllOption, \
                              VersionNotKnown
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
                     help='registry path from which to download Ceph base container image'),
        click.option('--salt/--ceph-salt', default=False,
                     help='Use "salt" (instead of "ceph-salt") to run ceph-salt formula'),
    ]
    return _decorator_composer(click_options, func)


def common_create_options(func):
    click_options = [
        click.option('--roles', type=str, default=None,
                     help='List of roles for each node. Example for two nodes: '
                          '[master, client, prometheus],[storage, mon, mgr]'),
        click.option('--os', type=click.Choice(['leap-15.1', 'leap-15.2', 'tumbleweed',
                                                'sles-12-sp3', 'sles-15-sp1', 'sles-15-sp2',
                                                'ubuntu-bionic']),
                     default=None, help='OS (open)SUSE distro'),
        click.option('--deploy/--no-deploy', default=True,
                     help="Don't run the deployment phase. Just generate the Vagrantfile"),
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
                     help="Include devel repo, if applicable"),
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
                     help='On VMS with additional disks, make one disk non-rotational')
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
def box():
    """
    Commands for manipulating Vagrant Boxes
    """


@box.command(name='list')
@libvirt_options
def list_boxes(**kwargs):
    """
    List all Vagrant Boxes installed in the system.
    """
    settings_dict = _gen_box_settings_dict(**kwargs)
    settings = Settings(**settings_dict)
    box_obj = Box(settings)
    box_names = box_obj.printable_list()
    if box_names:
        click.echo("List of all Vagrant Boxes installed in the system")
        click.echo("-------------------------------------------------")
    for box_name in box_names:
        click.echo(box_name)


@box.command(name='remove')
@click.argument('box_name', required=False)
@libvirt_options
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              help='Allow to remove Vagrant Box(es) without user confirmation',
              )
@click.option('--all-boxes', '--all', is_flag=True, help='Remove all Vagrant Boxes in the system')
def remove_box(box_name, **kwargs):
    """
    Remove a Vagrant Box installed in the system by sesdev.

    This involves first removing the corresponding image from the libvirt
    storage pool, and then running 'vagrant box remove' on it.
    """
    settings_dict = _gen_box_settings_dict(**kwargs)
    interactive = not settings_dict.get('non_interactive', False)
    settings = Settings(**settings_dict)
    box_obj = Box(settings)
    #
    # determine which box(es) are to be removed
    remove_all_boxes = kwargs.get('all_boxes', False)
    boxes_to_remove = None
    if remove_all_boxes:
        boxes_to_remove = box_obj.printable_list()
    else:
        if box_name:
            if not box_obj.exists(box_name):
                # but it might be an alias
                if box_name in Constant.OS_BOX_ALIASES:
                    dealiased_box_name = Constant.OS_BOX_ALIASES[box_name]
                    if box_obj.exists(dealiased_box_name):
                        box_name = dealiased_box_name
                    else:
                        raise BoxDoesNotExist(box_name)
                else:
                    raise BoxDoesNotExist(box_name)
            boxes_to_remove = [box_name]
        else:
            raise RemoveBoxNeedsBoxNameOrAllOption
    box_word = None
    if boxes_to_remove:
        box_word = _box_singular_or_plural(boxes_to_remove)
    else:
        return None
    if interactive:
        if boxes_to_remove:
            click.echo("You have asked to remove the following Vagrant Boxes")
            click.echo("----------------------------------------------------")
            for box_to_remove in boxes_to_remove:
                click.echo(box_to_remove)
            click.echo()
        really_want_to = click.confirm(
            'Do you really want to remove {} {}'.format(len(boxes_to_remove), box_word),
            default=True,
        )
        if not really_want_to:
            raise click.Abort()
    #
    # remove the boxes
    deps = Deployment.list(True)
    problems_encountered = False
    boxes_removed_count = 0
    for box_being_removed in boxes_to_remove:
        Log.info("Attempting to remove Vagrant Box ->{}<- ...".format(box_being_removed))
        #
        # existing deployments might be using this box
        existing_deployments = []
        for dep in deps:
            if box_being_removed == dep.settings.os:
                existing_deployments.append(dep.dep_id)
        if existing_deployments:
            if len(existing_deployments) == 1:
                Log.warning("The following deployment is already using Vagrant Box ->{}<-:"
                            .format(box_being_removed)
                            )
            else:
                Log.warning("The following deployments are already using Vagrant Box ->{}<-:"
                            .format(box_being_removed)
                            )
            for dep_id in existing_deployments:
                Log.warning("        {}".format(dep_id))
            click.echo()
            if len(existing_deployments) == 1:
                Log.warning("It must be destroyed first!")
            else:
                Log.warning("These must be destroyed first!")
            problems_encountered = True
            continue
        image_to_remove = box_obj.get_image_by_box(box_being_removed)
        if image_to_remove:
            Log.info("Found related image ->{}<- in libvirt storage pool"
                     .format(image_to_remove))
            box_obj.remove_image(image_to_remove)
            Log.info("Libvirt image removed.")
        box_obj.remove_box(box_being_removed)
        Log.info("Vagrant Box ->{}<- removed.".format(box_being_removed))
        boxes_removed_count += 1
    if boxes_removed_count != 1:
        click.echo("{} Vagrant Boxes were removed".format(boxes_removed_count))
    if problems_encountered:
        Log.warning("sesdev tried to remove {} Vagrant Box(es), but "
                    "problems were encountered."
                    .format(len(boxes_to_remove))
                    )
        click.echo("Use \"sesdev box list\" to check current state")
    return None


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


def _gen_box_settings_dict(libvirt_host,
                           libvirt_user,
                           libvirt_private_key_file,
                           libvirt_storage_pool,
                           libvirt_networks,
                           all_boxes=None,
                           non_interactive=None,
                           force=None,
                           ):
    settings_dict = {}

    if all_boxes:
        pass

    if non_interactive or force:
        settings_dict['non_interactive'] = True

    if libvirt_host:
        settings_dict['libvirt_host'] = libvirt_host

    if libvirt_user:
        settings_dict['libvirt_user'] = libvirt_user

    if libvirt_private_key_file:
        settings_dict['libvirt_private_key_file'] = libvirt_private_key_file

    if libvirt_storage_pool:
        settings_dict['libvirt_storage_pool'] = libvirt_storage_pool

    if libvirt_networks:
        settings_dict['libvirt_networks'] = libvirt_networks

    return settings_dict


def _gen_settings_dict(
        version,
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
        image_path=None,
        ipv6=None,
        libvirt_host=None,
        libvirt_networks=None,
        libvirt_private_key_file=None,
        libvirt_storage_pool=None,
        libvirt_user=None,
        non_interactive=None,
        num_disks=None,
        os=None,
        qa_test_opt=None,
        ram=None,
        repo=None,
        repo_priority=None,
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
        if version in ['ses7', 'octopus', 'pacific']:
            roles_string = Constant.ROLES_SINGLE_NODE['octopus']
        elif version in ['ses6', 'nautilus']:
            roles_string = Constant.ROLES_SINGLE_NODE['nautilus']
        elif version in ['ses5']:
            roles_string = Constant.ROLES_SINGLE_NODE['luminous']
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
        settings_dict['filestore_osds'] = False
    else:
        settings_dict['filestore_osds'] = True
        if not disk_size:
            settings_dict['disk_size'] = 15  # default 8 GB disk size is too small for FileStore

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

    if version is not None:
        settings_dict['version'] = version

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
                    'url': repo_url,
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

    if image_path is not None:
        settings_dict['image_path'] = image_path

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
            if not all([path.isabs(x) for x in [src, dst]]):
                raise OptionValueError('--synced-folder',
                                       "Please provide absolute paths for "
                                       "synced folder paths",
                                       folder)
            if not path.exists(src):
                raise OptionValueError('--synced-folder',
                                       "Path to the source synced folder must exist",
                                       src)

        except ValueError as exc:
            raise OptionFormatError('--synced-folder', "src:dst", folder) from exc
    settings_dict['synced_folder'] = [folder.split(':') for folder in synced_folder]

    return settings_dict


def _create_command(deployment_id, deploy, settings_dict):
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
    if deploy:
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
                click.echo("=== Deployment Finished ===")
                click.echo()
                click.echo("You can login into the cluster with:")
                click.echo()
                click.echo("  $ sesdev ssh {}".format(deployment_id))
                click.echo()
                if dep.settings.version == 'ses5':
                    click.echo("Or, access openATTIC with:")
                    click.echo()
                    click.echo("  $ sesdev tunnel {} openattic".format(deployment_id))
                elif dep.settings.version == 'octopus' and dep.has_suma():
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
def ses5(deployment_id, deploy, **kwargs):
    """
    Creates a SES5 cluster using SLES-12-SP3
    """
    _prep_kwargs(kwargs)
    if not kwargs['bluestore']:
        # sesdev does not (yet) support --filestore for ses5 deployments
        raise OptionNotSupportedInVersion('--filestore', 'ses5')
    settings_dict = _gen_settings_dict('ses5', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses5', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@libvirt_options
def ses6(deployment_id, deploy, **kwargs):
    """
    Creates a SES6 cluster using SLES-15-SP1
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('ses6', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses6', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def ses7(deployment_id, deploy, **kwargs):
    """
    Creates a SES7 cluster using SLES-15-SP2 and packages (and container image)
    from the Devel:Storage:7.0 IBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('ses7', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses7', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@libvirt_options
def nautilus(deployment_id, deploy, **kwargs):
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
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def octopus(deployment_id, deploy, **kwargs):
    """
    Creates a Ceph Octopus cluster using openSUSE Leap 15.2 and packages
    (and container image) from filesystems:ceph:octopus:upstream OBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('octopus', **kwargs)
    deployment_id = _maybe_gen_dep_id('octopus', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@ipv6_options
def pacific(deployment_id, deploy, **kwargs):
    """
    Creates a Ceph Pacific cluster using openSUSE Leap 15.2 and packages
    (and container image) from filesystems:ceph:master:upstream OBS project
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('pacific', **kwargs)
    deployment_id = _maybe_gen_dep_id('pacific', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@libvirt_options
@click.option("--deploy-ses", is_flag=True, default=False,
              help="Deploy SES using rook in CaasP")
def caasp4(deployment_id, deploy, **kwargs):
    """
    Creates a CaaSP cluster using SLES 15 SP2
    """
    _prep_kwargs(kwargs)
    settings_dict = _gen_settings_dict('caasp4', **kwargs)
    deployment_id = _maybe_gen_dep_id('caasp4', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


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
def makecheck(deployment_id, deploy, **kwargs):
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
    _create_command(deployment_id, deploy, settings_dict)


def _is_a_glob(a_string):
    """
    Return True or False depending on whether a_string appears to be a glob
    """
    pattern = re.compile(r'[\*\[\]\{\}\?]')
    return bool(pattern.search(a_string))


def _maybe_glob_deps(deployment_id):
    matching_deployments = None
    if _is_a_glob(deployment_id):
        deps = Deployment.list(True)
        dep_ids = [d.dep_id for d in deps]
        matching_dep_ids = fnmatch.filter(dep_ids, deployment_id)
        matching_deployments = [d for d in deps if d.dep_id in matching_dep_ids]
    else:
        matching_deployments = [Deployment.load(deployment_id)]
    return matching_deployments


def _box_singular_or_plural(an_iterable):
    if len(an_iterable) == 1:
        return "Vagrant Box"
    return "Vagrant Boxes"


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
            url=kwargs['custom_repo'],
            priority=Constant.ZYPPER_PRIO_ELEVATED if kwargs['repo_priority'] else None
        )
    dep.add_repo_subcommand(custom_repo, kwargs['update'], _print_log)


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


@click.option('--format', 'format_opt', type=str, default=None)
@cli.command(name='list')
def list_deps(format_opt):
    """
    Lists all the available deployments.
    """
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
        status = None
        for node in nodes.values():
            if status is None:
                status = node.status
            elif node.status == 'running' and status == 'not deployed':
                status = 'partially deployed'
            elif node.status == 'stopped' and status == 'running':
                status = 'partially running'
            elif node.status == 'suspended' and status == 'running':
                status = 'partially running'
            elif node.status == 'running' and status == 'stopped':
                status = 'partially running'
            elif node.status == 'running' and status == 'suspended':
                status = 'partially running'
        return status

    if format_opt not in ['json']:
        p_table = PrettyTable(["ID", "Version", "Status", "Nodes"])
        p_table.align = "l"

    for dep in deps:
        Log.debug("_status: Looping over deployments ({})".format(dep.dep_id))
        status = str(_status(dep.nodes))
        Log.debug("_status: -> status: {}".format(status))
        version = getattr(dep.settings, 'version', None)
        Log.debug("_status: -> version: {}".format(version))
        nodes = getattr(dep, 'nodes', None)
        node_names = '(unknown)' if nodes is None else ', '.join(nodes)
        Log.debug("_status: -> node_names: {}".format(node_names))
        if format_opt in ['json']:
            deployments_list.append({
                "id": dep.dep_id,
                "version": version,
                "status": status,
                "nodes": list(nodes),
            })
        else:
            p_table.add_row([dep.dep_id, version, status, node_names])
    if format_opt in ['json']:
        click.echo(json.dumps(deployments_list, sort_keys=True, indent=4))
    else:
        deployment_word = "deployments" if len(deps) > 1 else "deployment"
        click.echo("Found {} {}:".format(len(deps), deployment_word))
        click.echo()
        click.echo(p_table)
        click.echo()


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
@click.argument('deployment_id')
def show(deployment_id, **kwargs):
    """
    Display the configuration of a running deployment - this is the same
    information that is displayed by the "create" command before asking the user
    whether they are really sure they want to create the cluster). Use "--detail"
    to get information on individual VMs in the deployment.
    """
    dep = Deployment.load(deployment_id)
    click.echo(dep.configuration_report(show_individual_vms=kwargs['detail']))


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
@click.argument('command', required=False, nargs=-1)
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
    if command:
        Log.info("Running SSH command on {}: {}".format(node_name, command))
    dep.ssh(node_name, command)


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
        dep.start(_print_log, node)
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
@click.argument('service', type=click.Choice(['dashboard', 'grafana', 'openattic', 'suma',
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
