import fnmatch
import logging
import re
import sys

import click
import pkg_resources
import seslib
from seslib.exceptions import SesDevException


logger = logging.getLogger(__name__)


def sesdev_main():
    seslib.GlobalSettings.init_path_to_qa(__file__)
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
        click.option('--deepsea-cli/--salt-run', default=True,
                     help="Use deepsea-cli or salt-run to execute DeepSea stages"),
        click.option('--stop-before-deepsea-stage', type=int, default=None,
                     help='Allows to stop deployment before running the specified DeepSea stage'),
        click.option('--deepsea-repo', type=str, default=None, help='DeepSea Git repo URL'),
        click.option('--deepsea-branch', type=str, default=None, help='DeepSea Git branch'),
    ]
    return _decorator_composer(click_options, func)


def ceph_salt_options(func):
    click_options = [
        click.option('--stop-before-ceph-salt-config', is_flag=True, default=False,
                     help='Allows to stop deployment configuring the cluster with ceph-salt'),
        click.option('--stop-before-ceph-salt-deploy', is_flag=True, default=False,
                     help='Allows to stop deployment deploying the cluster with ceph-salt'),
        click.option('--ceph-salt-repo', type=str, default=None,
                     help='ceph-salt Git repo URL'),
        click.option('--ceph-salt-branch', type=str, default=None,
                     help='ceph-salt Git branch'),
        click.option('--image-path', type=str, default=None,
                     help='registry path from which to download Ceph container image'),
        click.option('--cephadm-bootstrap/--no-cephadm-bootstrap', default=True,
                     help='Run cephadm bootstrap during deployment. '
                          '(If false all other --deploy-* options will be disabled)'),
        click.option('--deploy-mons/--no-deploy-mons', default=True, help='Deploy Ceph Mons'),
        click.option('--deploy-mgrs/--no-deploy-mgrs', default=True, help='Deploy Ceph Mgrs'),
        click.option('--deploy-osds/--no-deploy-osds', default=True, help='Deploy Ceph OSDs'),
        click.option('--ceph-salt-deploy/--no-ceph-salt-deploy', default=True,
                     help='Use `ceph-salt deploy` command to run ceph-salt formula'),
    ]
    return _decorator_composer(click_options, func)


def common_create_options(func):
    click_options = [
        click.option('--roles', type=str, default=None,
                     help='List of roles for each node. Example for two nodes: '
                          '[master, client, prometheus],[storage, mon, mgr]'),
        click.option('--os', type=click.Choice(['leap-15.1', 'leap-15.2', 'tumbleweed',
                                                'sles-12-sp3', 'sles-15-sp1', 'sles-15-sp2']),
                     default=None, help='OS (open)SUSE distro'),
        click.option('--vagrant-box', type=str, default=None,
                     help='Vagrant box to use in deployment'),
        click.option('--deploy/--no-deploy', default=True,
                     help="Don't run the deployment phase. Just generated the Vagrantfile"),
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
        click.option('--repo', multiple=True, type=str, default=None,
                     help='Custom zypper repo URL. The repo will be added to each node.'),
        click.option('--repo-priority/--no-repo-priority', default=True,
                     help="Automatically set priority on custom zypper repos"),
        click.option('--qa-test/--no-qa-test', 'qa_test_opt', default=False,
                     help="Automatically run integration tests on the deployed cluster"),
        click.option('--scc-user', type=str, default=None,
                     help='SCC organization username'),
        click.option('--scc-pass', type=str, default=None,
                     help='SCC organization password'),
        click.option('--domain', type=str, default='{}.com',
                     help='Domain name to use'),
        click.option('--non-interactive', '-n', '--force', '-f', is_flag=True, default=False,
                     help='Do not ask the user if they really want to'),
        click.option('--encrypted-osds', is_flag=True, default=False,
                     help='Deploy OSDs encrypted'),
    ]
    return _decorator_composer(click_options, func)


def _parse_roles(roles):
    roles = "".join(roles.split())
    if roles.startswith('[[') and roles.endswith(']]'):
        roles = roles[1:-1]
    roles = roles.split(",")
    log_msg = "_parse_roles: raw roles from user: {}".format(roles)
    logger.debug(log_msg)
    log_msg = "_parse_roles: pre-processed roles array: {}".format(roles)
    logger.debug(log_msg)
    _roles = []
    _node = None
    for role in roles:
        if role.startswith('['):
            _node = []
            if role.endswith(']'):
                role = role[1:-1]
                if role:
                    _node.append(role)
                    _node = list(set(_node))  # eliminate duplicate roles
                _node.sort()
                _roles.append(_node)
            else:
                role = role[1:]
                _node.append(role)
        elif role.endswith(']'):
            role = role[:-1]
            _node.append(role)
            _node = list(set(_node))  # eliminate duplicate roles
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
            dep_id += "_mini"
    return dep_id


@click.group()
@click.option('-w', '--work-path', required=False,
              type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help='Filesystem path to store deployments')
@click.option('-c', '--config-file', required=False,
              type=click.Path(exists=True, dir_okay=False, file_okay=True),
              help='Configuration file location')
@click.option('--debug/--no-debug', default=False,
              help='Whether to emit DEBUG-level log messages')
@click.option('--log-file', type=str, default=None)
@click.option('--vagrant-debug/--no-vagrant-debug', default=False,
              help='Whether to run vagrant with --debug option')
@click.version_option(pkg_resources.get_distribution('sesdev'), message="%(version)s")
def cli(work_path=None, config_file=None, debug=False, log_file=None, vagrant_debug=False):
    """
    Welcome to the sesdev tool.

    Usage examples:

    # Deployment of single node SES6 cluster:

        $ sesdev create ses6 --single-node my_ses6_cluster

    # Deployment of Octopus cluster where each storage node contains 4 10G disks for
OSDs:

        \b
$ sesdev create octopus --roles="[master, mon, mgr], \\
       [storage, mon, mgr, mds], [storage, mon, mds]" \\
       --num-disks=4 --disk-size=10 my_octopus_cluster

    """
    if debug:
        logger.info("Debug mode: ON")
        seslib.GlobalSettings.DEBUG = debug

    if vagrant_debug:
        logger.info("vagrant will be run with --debug option")
        seslib.GlobalSettings.VAGRANT_DEBUG = vagrant_debug

    if log_file:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            filename=log_file, filemode='w',
                            level=logging.DEBUG if debug else logging.INFO)
    else:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            level=logging.CRITICAL)

    if work_path:
        logger.info("Working path: %s", work_path)
        seslib.GlobalSettings.A_WORKING_DIR = work_path

    if config_file:
        logger.info("Config file: %s", config_file)
        seslib.GlobalSettings.CONFIG_FILE = config_file


@cli.command(name='list')
def list_deps():
    """
    Lists all the available deployments.
    """
    deps = seslib.Deployment.list(True)
    log_msg = "Found deployments: {}".format(", ".join(d.dep_id for d in deps))
    logger.debug(log_msg)

    click.echo("| {:^11} | {:^10} | {:^15} | {:^60} |".format("Deployments", "Version", "Status",
                                                              "VMs"))
    click.echo("{}".format('-' * 109))

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

    for dep in deps:
        logger.debug("Looping over deployments: %s", dep.dep_id)
        status = str(_status(dep.nodes))
        logger.debug("-> status: %s", status)
        version = getattr(dep.settings, 'version', None)
        logger.debug("-> version: %s", version)
        nodes = getattr(dep, 'nodes', None)
        node_names = '(unknown)' if nodes is None else ', '.join(nodes)
        logger.debug("-> node_names: %s", node_names)
        click.echo("| {:<11} | {:<10} | {:<15} | {:<60} |"
                   .format(dep.dep_id, version, status, node_names))
    click.echo()


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
    click.echo("List of all Vagrant Boxes installed in the system")
    click.echo("-------------------------------------------------")
    settings_dict = _gen_box_settings_dict(**kwargs)
    settings = seslib.Settings(**settings_dict)
    box_obj = seslib.Box(settings)
    box_obj.list()


@box.command(name='remove')
@click.argument('box_name')
@libvirt_options
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              callback=_abort_if_false,
              expose_value=False,
              help='Allow to remove Vagrant Box without user confirmation',
              prompt='Are you sure you want to remove the Vagrant Box?',
              )
def remove_box(box_name, **kwargs):
    """
    Remove a Vagrant Box installed in the system by sesdev.

    This involves first removing the corresponding image from the libvirt
    storage pool, and then running 'vagrant box remove' on it.
    """
    settings_dict = _gen_box_settings_dict(**kwargs)
    settings = seslib.Settings(**settings_dict)
    #
    # existing deployments might be using this box
    deps = seslib.Deployment.list(True)
    existing_deployments = []
    for dep in deps:
        if box_name == dep.settings.os:
            existing_deployments.append(dep.dep_id)
    if existing_deployments:
        if len(existing_deployments) == 1:
            click.echo("The following deployment is already using box ->{}<-:"
                       .format(box_name))
        else:
            click.echo("The following deployments are already using box ->{}<-:"
                       .format(box_name))
        for dep_id in existing_deployments:
            click.echo("        {}".format(dep_id))
        click.echo()
        if len(existing_deployments) == 1:
            click.echo("It must be destroyed first!")
        else:
            click.echo("These must be destroyed first!")
        sys.exit(-1)

    box_obj = seslib.Box(settings)

    if box_obj.exists(box_name):
        click.echo("Proceeding to remove Vagrant Box ->{}<-".format(box_name))
    else:
        click.echo("There is no Vagrant Box called ->{}<-".format(box_name))
        sys.exit(-1)

    image_to_remove = box_obj.get_image_by_box(box_name)
    if image_to_remove:
        click.echo("Found related image ->{}<- in libvirt storage pool"
                   .format(image_to_remove))
        box_obj.remove_image(image_to_remove)
        click.echo("Libvirt image removed.")

    box_obj.remove_box(box_name)
    click.echo("Vagrant Box removed.")


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
                           libvirt_networks):
    settings_dict = {}

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


def _gen_settings_dict(version,
                       roles,
                       os,
                       num_disks,
                       single_node,
                       libvirt_host,
                       libvirt_user,
                       libvirt_private_key_file,
                       libvirt_storage_pool,
                       libvirt_networks,
                       repo,
                       cpus,
                       ram,
                       disk_size,
                       repo_priority,
                       qa_test_opt,
                       vagrant_box,
                       scc_user,
                       scc_pass,
                       domain,
                       non_interactive,
                       encrypted_osds,
                       deepsea_cli=None,
                       stop_before_deepsea_stage=None,
                       deepsea_repo=None,
                       deepsea_branch=None,
                       ceph_salt_repo=None,
                       ceph_salt_branch=None,
                       stop_before_ceph_salt_config=False,
                       stop_before_ceph_salt_deploy=False,
                       image_path=None,
                       cephadm_bootstrap=True,
                       deploy_mons=True,
                       deploy_mgrs=True,
                       deploy_osds=True,
                       ceph_salt_deploy=True,
                       ):

    settings_dict = {}
    if not single_node and roles:
        settings_dict['roles'] = _parse_roles(roles)
    elif single_node:
        if version in ['ses7', 'octopus', 'pacific']:
            settings_dict['roles'] = _parse_roles(
                "[ master, bootstrap, storage, mon, mgr, prometheus, grafana, mds, "
                "igw, rgw, ganesha ]"
                )
        elif version in ['ses5']:
            settings_dict['roles'] = _parse_roles(
                "[ master, bootstrap, storage, mon, mgr, mds, igw, rgw, ganesha ]"
                )
        else:
            settings_dict['roles'] = _parse_roles(
                "[ master, storage, mon, mgr, prometheus, grafana, mds, igw, rgw, "
                "ganesha ]"
                )

    if single_node:
        settings_dict['single_node'] = single_node

    if os:
        settings_dict['os'] = os

    if cpus:
        settings_dict['cpus'] = cpus

    if ram:
        settings_dict['ram'] = ram

    if num_disks:
        settings_dict['num_disks'] = num_disks
        settings_dict['explicit_num_disks'] = True
    else:
        settings_dict['explicit_num_disks'] = False

    if disk_size:
        settings_dict['disk_size'] = disk_size

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

    if deepsea_cli is not None:
        settings_dict['use_deepsea_cli'] = deepsea_cli

    if stop_before_deepsea_stage is not None:
        settings_dict['stop_before_stage'] = stop_before_deepsea_stage

    if deepsea_repo:
        settings_dict['deepsea_git_repo'] = deepsea_repo

    if deepsea_branch:
        settings_dict['deepsea_git_branch'] = deepsea_branch

    if version is not None:
        settings_dict['version'] = version

    if repo:
        settings_dict['repos'] = list(repo)

    if repo_priority is not None:
        settings_dict['repo_priority'] = repo_priority

    if qa_test_opt is not None:
        settings_dict['qa_test'] = qa_test_opt

    if vagrant_box:
        settings_dict['vagrant_box'] = vagrant_box

    if scc_user:
        settings_dict['scc_username'] = scc_user

    if scc_pass:
        settings_dict['scc_password'] = scc_pass

    if domain:
        settings_dict['domain'] = domain

    if non_interactive:
        settings_dict['non_interactive'] = non_interactive

    if encrypted_osds:
        settings_dict['encrypted_osds'] = encrypted_osds

    if ceph_salt_repo:
        if not ceph_salt_branch:
            logger.debug(
                "User explicitly specified only --ceph-salt-repo; assuming --ceph-salt-branch %s",
                seslib.GlobalSettings.CEPH_SALT_BRANCH
                )
            ceph_salt_branch = seslib.GlobalSettings.CEPH_SALT_BRANCH

    if ceph_salt_branch:
        if not ceph_salt_repo:
            logger.debug(
                "User explicitly specified only --ceph-salt-branch; assuming --ceph-salt-repo %s",
                seslib.GlobalSettings.CEPH_SALT_REPO
                )
            ceph_salt_repo = seslib.GlobalSettings.CEPH_SALT_REPO

    if ceph_salt_repo:
        settings_dict['ceph_salt_git_repo'] = ceph_salt_repo

    if ceph_salt_branch:
        settings_dict['ceph_salt_git_branch'] = ceph_salt_branch

    if stop_before_ceph_salt_config:
        settings_dict['stop_before_ceph_salt_config'] = stop_before_ceph_salt_config

    if stop_before_ceph_salt_deploy:
        settings_dict['stop_before_ceph_salt_deploy'] = stop_before_ceph_salt_deploy

    if image_path:
        settings_dict['image_path'] = image_path

    if not cephadm_bootstrap:
        settings_dict['ceph_salt_cephadm_bootstrap'] = False
        settings_dict['ceph_salt_deploy_mons'] = False
        settings_dict['ceph_salt_deploy_mgrs'] = False
        settings_dict['ceph_salt_deploy_osds'] = False

    if not deploy_mons:
        settings_dict['ceph_salt_deploy_mons'] = False

    if not deploy_mgrs:
        settings_dict['ceph_salt_deploy_mgrs'] = False

    if not deploy_osds:
        settings_dict['ceph_salt_deploy_osds'] = False

    if not ceph_salt_deploy:
        settings_dict['ceph_salt_deploy'] = False

    return settings_dict


def _create_command(deployment_id, deploy, settings_dict):
    settings = seslib.Settings(**settings_dict)
    dep = seslib.Deployment.create(deployment_id, settings)
    really_want_to = None
    click.echo("=== Creating deployment \"{}\" with the following configuration ==="
               .format(deployment_id)
               )
    click.echo(dep.status())
    if deploy:
        if getattr(settings, 'non_interactive', False):
            really_want_to = True
        else:
            really_want_to = click.confirm(
                'Do you want to continue with the deployment?',
                default=True,
                )
        try:
            if really_want_to:
                dep.vet_configuration()
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


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@libvirt_options
def ses5(deployment_id, deploy, **kwargs):
    """
    Creates a SES5 cluster using SLES-12-SP3
    """
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
    settings_dict = _gen_settings_dict('ses6', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses6', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@click.option("--use-deepsea/--use-cephadm", default=False,
              help="Use deepsea to deploy SES7 instead of cephadm")
def ses7(deployment_id, deploy, use_deepsea, **kwargs):
    """
    Creates a SES7 cluster using SLES-15-SP2 and packages (and container image)
    from the Devel:Storage:7.0 IBS project
    """
    settings_dict = _gen_settings_dict('ses7', **kwargs)
    deployment_id = _maybe_gen_dep_id('ses7', deployment_id, settings_dict)
    if use_deepsea:
        settings_dict['deployment_tool'] = 'deepsea'
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
    settings_dict = _gen_settings_dict('nautilus', **kwargs)
    deployment_id = _maybe_gen_dep_id('nautilus', deployment_id, settings_dict)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@click.option("--use-deepsea/--use-cephadm", default=False,
              help="Use deepsea to deploy Ceph Octopus instead of cephadm")
def octopus(deployment_id, deploy, use_deepsea, **kwargs):
    """
    Creates a Ceph Octopus cluster using openSUSE Leap 15.2 and packages
    (and container image) from filesystems:ceph:octopus:upstream OBS project
    """
    settings_dict = _gen_settings_dict('octopus', **kwargs)
    deployment_id = _maybe_gen_dep_id('octopus', deployment_id, settings_dict)
    if use_deepsea:
        settings_dict['deployment_tool'] = 'deepsea'
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@deepsea_options
@ceph_salt_options
@libvirt_options
@click.option("--use-deepsea/--use-cephadm", default=False,
              help="Use deepsea to deploy Ceph Master Branch instead of cephadm")
def pacific(deployment_id, deploy, use_deepsea, **kwargs):
    """
    Creates a Ceph Pacific cluster using openSUSE Leap 15.2 and packages
    (and container image) from filesystems:ceph:master:upstream OBS project
    """
    settings_dict = _gen_settings_dict('pacific', **kwargs)
    deployment_id = _maybe_gen_dep_id('pacific', deployment_id, settings_dict)
    if use_deepsea:
        settings_dict['deployment_tool'] = 'deepsea'
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id', required=False)
@common_create_options
@libvirt_options
@click.option("--deploy-ses", is_flag=True, default=False,
              help="Deploy SES using rook in CaasP")
def caasp4(deployment_id, deploy, deploy_ses, **kwargs):
    """
    Creates a CaaSP cluster using SLES 15 SP1
    """
    if kwargs['num_disks'] is None:
        kwargs['num_disks'] = 2 if deploy_ses else 0
    settings_dict = _gen_settings_dict('caasp4', **kwargs)
    deployment_id = _maybe_gen_dep_id('caasp4', deployment_id, settings_dict)
    if deploy_ses:
        settings_dict['caasp_deploy_ses'] = True
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
        deps = seslib.Deployment.list(True)
        dep_ids = [d.dep_id for d in deps]
        matching_dep_ids = fnmatch.filter(dep_ids, deployment_id)
        matching_deployments = [d for d in deps if d.dep_id in matching_dep_ids]
    else:
        matching_deployments = [seslib.Deployment.load(deployment_id)]
    return matching_deployments


def _cluster_singular_or_plural(an_iterable):
    if len(an_iterable) == 1:
        return "cluster"
    return "clusters"


@cli.command()
@click.argument('deployment_id')
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              help='Allow to destroy the deployment without user confirmation',
              )
@click.option('--destroy-networks', is_flag=True, default=False,
              help='Allow to destroy networks associated with the deployment')
def destroy(deployment_id, non_interactive, destroy_networks):
    """
    Destroys the deployment(s) named DEPLOYMENT_SPEC -- where DEPLOYMENT_SPEC might
    be either a literal deployment ID or a glob ("octopus_*") -- by destroying the
    VMs and deleting the deployment directory.
    """
    matching_deployments = _maybe_glob_deps(deployment_id)
    cluster_word = _cluster_singular_or_plural(matching_deployments)
    if not non_interactive:
        really_want_to = click.confirm(
            'Do you really want to destroy {} {}'.format(len(matching_deployments), cluster_word),
            default=True,
            )
        if not really_want_to:
            raise click.Abort()
    for dep in matching_deployments:
        logger.debug("destroy deployment: '%s', destroy networks: %s",
                     deployment_id,
                     destroy_networks)
        dep.destroy(_print_log, destroy_networks)


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
    dep = seslib.Deployment.load(deployment_id)
    _node = 'master' if node is None else node
    if command:
        log_msg = "SSH command: {}".format(command)
        logger.info(log_msg)
    dep.ssh(_node, command)


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
    dep = seslib.Deployment.load(deployment_id)
    dep.scp(source, destination, recurse=recursive)


@cli.command()
@click.argument('deployment_id')
def qa_test(deployment_id):
    """
    Runs QA test on an already-deployed cluster.
    """
    dep = seslib.Deployment.load(deployment_id)
    dep.qa_test(_print_log)


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
    dep = seslib.Deployment.load(deployment_id)
    _node = 'master' if node is None else node
    dep.supportconfig(_print_log, _node)


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


@cli.command()
@click.argument('deployment_id')
def show(deployment_id):
    """
    Shows the information of deployment DEPLOYMENT_ID
    """
    dep = seslib.Deployment.load(deployment_id)
    click.echo(dep.status())


@cli.command()
@click.argument('deployment_id')
@click.option('--non-interactive', '-n', '--force', '-f',
              is_flag=True,
              callback=_abort_if_false,
              expose_value=False,
              help='Allow to redeploy the cluster without user confirmation',
              prompt='Are you sure you want to redeploy the cluster?')
def redeploy(deployment_id):
    """
    Destroys the VMs of the deployment DEPLOYMENT_ID and deploys again the cluster
    from scratch with the same configuration.
    """
    dep = seslib.Deployment.load(deployment_id)
    dep.destroy(_print_log)
    dep = seslib.Deployment.create(deployment_id, dep.settings)
    dep.start(_print_log)


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
    if service:
        click.echo("Opening tunnel to service '{}' on node '{}'...".format(service, node))
    elif remote_port:
        click.echo("Opening tunnel between remote {} port and local {} port on node {}"
                   .format(remote_port, local_port if local_port else remote_port, node))
    dep = seslib.Deployment.load(deployment_id)
    dep.start_port_forwarding(service, node, remote_port, local_port, local_address)


if __name__ == '__main__':
    sys.exit(sesdev_main())
