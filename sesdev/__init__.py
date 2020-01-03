import logging
import sys

import click
import pkg_resources
import seslib
from seslib.exceptions import SesDevException


logger = logging.getLogger(__name__)


def sesdev_main():
    try:
        # pylint: disable=unexpected-keyword-arg
        cli(prog_name='sesdev')
    except SesDevException as ex:
        logger.exception(ex)
        click.echo(str(ex))


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


def ceph_bootstrap_options(func):
    click_options = [
        click.option('--stop-before-ceph-bootstrap-config', is_flag=True, default=False,
                     help='Allows to stop deployment configuring the cluster with ceph-bootstrap'),
        click.option('--stop-before-ceph-bootstrap-deploy', is_flag=True, default=False,
                     help='Allows to stop deployment deploying the cluster with ceph-bootstrap'),
        click.option('--ceph-bootstrap-repo', type=str, default=None,
                     help='ceph-bootstrap Git repo URL'),
        click.option('--ceph-bootstrap-branch', type=str, default=None,
                     help='ceph-bootstrap Git branch'),
        click.option('--ceph-container-image', type=str, default=None,
                     help='container image path for Ceph daemons'),
        click.option('--deploy-bootstrap', is_flag=True, default=True,
                     help='Run ceph-daemon bootstrap during deployment. '
                          '(If false all other --deploy-* options will be disabled)'),
        click.option('--deploy-mons', is_flag=True, default=True, help='Deploy Ceph Mons'),
        click.option('--deploy-mgrs', is_flag=True, default=True, help='Deploy Ceph Mgrs'),
        click.option('--deploy-osds', is_flag=True, default=True, help='Deploy Ceph OSDs'),
    ]
    return _decorator_composer(click_options, func)


def common_create_options(func):
    click_options = [
        click.option('--roles', type=str, default=None,
                     help='List of roles for each node. Example for two nodes: '
                          '[admin, client, prometheus],[storage, mon, mgr]'),
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
        click.option('--scc-user', type=str, default=None,
                     help='SCC organization username'),
        click.option('--scc-pass', type=str, default=None,
                     help='SCC organization password'),
        click.option('--domain', type=str, default='{}.com',
                     help='Domain name to use'),
    ]
    return _decorator_composer(click_options, func)


def _parse_roles(roles):
    roles = [r.strip() for r in roles.split(",")]
    _roles = []
    _node = None
    for role in roles:
        role = role.strip()
        if role.startswith('['):
            _node = []
            if role.endswith(']'):
                role = role[1:-1].strip()
                _node.append(role)
                _node = list(set(_node))  # eliminate duplicate roles
                _roles.append(_node)
            else:
                role = role[1:].strip()
                _node.append(role)
        elif role.endswith(']'):
            role = role[:-1].strip()
            _node.append(role)
            _node = list(set(_node))  # eliminate duplicate roles
            _roles.append(_node)
        else:
            role = role.strip()
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


@click.group()
@click.option('-w', '--work-path', required=False,
              type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help='Filesystem path to store deployments')
@click.option('-c', '--config-file', required=False,
              type=click.Path(exists=True, dir_okay=False, file_okay=True),
              help='Configuration file location')
@click.option('--debug/--no-debug', default=False)
@click.option('--log-file', type=str, default=None)
@click.version_option(pkg_resources.get_distribution('sesdev'), message="%(version)s")
def cli(work_path=None, config_file=None, debug=False, log_file=None):
    """
    Welcome to the sesdev tool.

    Usage examples:

    # Deployment of single node SES6 cluster:

        $ sesdev create ses6 --single-node my_ses6_cluster

    # Deployment of Octopus cluster where each storage node contains 4 10G disks for
OSDs:

        \b
$ sesdev create octopus --roles="[admin, mon, mgr], \\
       [storage, mon, mgr, mds], [storage, mon, mds]" \\
       --num-disks=4 --disk-size=10 my_octopus_cluster

    """
    if log_file:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            filename=log_file, filemode='w',
                            level=logging.INFO if not debug else logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            level=logging.CRITICAL)

    if work_path:
        logger.info("Working path: %s", work_path)
        seslib.GlobalSettings.WORKING_DIR = work_path

    if config_file:
        logger.info("Config file: %s", config_file)
        seslib.GlobalSettings.CONFIG_FILE = config_file


@cli.command(name='list')
def list_deps():
    """
    Lists all the available deployments.
    """
    deps = seslib.Deployment.list(True)
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
        status = _status(dep.nodes)
        click.echo("| {:<11} | {:<10} | {:<15} | {:<60} |"
                   .format(dep.dep_id, dep.settings.version, status, ", ".join(dep.nodes)))
    click.echo()


@cli.group()
def create():
    """
    Creates a new Vagrant based SES cluster.

    It creates a deployment directory in <working_directory>/<deployment_id>
    with a Vagrantfile inside, and calls `vagrant up` to start the deployment.

    By default <working_directory> is located in `~/.sesdev`.

    Checks all the options available with:

    $ sesdev create --help
    """


def _count_storage_nodes(roles):
    return len([node for node in roles if 'storage' in node])


def _gen_settings_dict(version,
                       roles,
                       os,
                       num_disks,
                       single_node,
                       libvirt_host,
                       libvirt_user,
                       libvirt_storage_pool,
                       libvirt_networks,
                       deepsea_cli,
                       stop_before_deepsea_stage,
                       deepsea_repo,
                       deepsea_branch,
                       repo,
                       cpus,
                       ram,
                       disk_size,
                       repo_priority,
                       vagrant_box,
                       scc_user,
                       scc_pass,
                       domain,
                       ceph_bootstrap_repo=None,
                       ceph_bootstrap_branch=None,
                       stop_before_ceph_bootstrap_config=False,
                       stop_before_ceph_bootstrap_deploy=False,
                       ceph_container_image=None,
                       deploy_bootstrap=True,
                       deploy_mons=True,
                       deploy_mgrs=True,
                       deploy_osds=True):

    settings_dict = {}
    if not single_node and roles:
        settings_dict['roles'] = _parse_roles(roles)
    elif single_node:
        settings_dict['roles'] = _parse_roles("["
                                              "   admin, storage, mon, mgr, prometheus,"
                                              "   grafana, mds, igw, rgw, ganesha"
                                              "]"
                                              )

    storage_nodes = None
    if 'roles' in settings_dict and settings_dict['roles']:
        storage_nodes = _count_storage_nodes(settings_dict['roles'])

    if os:
        settings_dict['os'] = os

    if num_disks:
        if storage_nodes and storage_nodes < 3 and num_disks < 3:
            num_disks = 3
        settings_dict['num_disks'] = num_disks
    else:
        if storage_nodes and storage_nodes < 3:
            settings_dict['num_disks'] = 3

    if cpus:
        settings_dict['cpus'] = cpus

    if ram:
        settings_dict['ram'] = ram

    if disk_size:
        settings_dict['disk_size'] = disk_size

    if libvirt_host:
        settings_dict['libvirt_host'] = libvirt_host

    if libvirt_user:
        settings_dict['libvirt_user'] = libvirt_user

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

    if vagrant_box:
        settings_dict['vagrant_box'] = vagrant_box

    if scc_user:
        settings_dict['scc_username'] = scc_user

    if scc_pass:
        settings_dict['scc_password'] = scc_pass

    if domain:
        settings_dict['domain'] = domain

    if ceph_bootstrap_repo:
        settings_dict['ceph_bootstrap_git_repo'] = ceph_bootstrap_repo

    if ceph_bootstrap_branch:
        settings_dict['ceph_bootstrap_git_branch'] = ceph_bootstrap_branch

    if stop_before_ceph_bootstrap_config:
        settings_dict['stop_before_ceph_bootstrap_config'] = stop_before_ceph_bootstrap_config

    if stop_before_ceph_bootstrap_deploy:
        settings_dict['stop_before_ceph_bootstrap_deploy'] = stop_before_ceph_bootstrap_deploy

    if ceph_container_image:
        settings_dict['ceph_container_image'] = ceph_container_image

    if not deploy_bootstrap:
        settings_dict['ceph_bootstrap_deploy_bootstrap'] = False
        settings_dict['ceph_bootstrap_deploy_mons'] = False
        settings_dict['ceph_bootstrap_deploy_mgrs'] = False
        settings_dict['ceph_bootstrap_deploy_osds'] = False

    if not deploy_mons:
        settings_dict['ceph_bootstrap_deploy_mons'] = False

    if not deploy_mgrs:
        settings_dict['ceph_bootstrap_deploy_mons'] = False

    if not deploy_osds:
        settings_dict['ceph_bootstrap_deploy_osds'] = False

    return settings_dict


def _create_command(deployment_id, deploy, settings_dict):
    settings = seslib.Settings(**settings_dict)
    dep = seslib.Deployment.create(deployment_id, settings)
    click.echo("=== Creating deployment with the following configuration ===")
    click.echo(dep.status())
    if deploy:
        try:
            if click.confirm('Do you want to continue with the deployment?', default=True):
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
@click.argument('deployment_id')
@common_create_options
@deepsea_options
@libvirt_options
def ses5(deployment_id, deploy, **kwargs):
    """
    Creates a SES5 cluster using SLES-12-SP3
    """
    settings_dict = _gen_settings_dict('ses5', **kwargs)
    if 'roles' in settings_dict and 'single_node' in kwargs and kwargs['single_node']:
        settings_dict['roles'][0].append("openattic")
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id')
@common_create_options
@deepsea_options
@libvirt_options
def ses6(deployment_id, deploy, **kwargs):
    """
    Creates a SES6 cluster using SLES-15-SP1
    """
    settings_dict = _gen_settings_dict('ses6', **kwargs)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id')
@common_create_options
@deepsea_options
@ceph_bootstrap_options
@libvirt_options
@click.option("--use-deepsea/--use-orchestrator", default=False,
              help="Use deepsea to deploy SES7 instead of SSH orchestrator")
def ses7(deployment_id, deploy, use_deepsea, **kwargs):
    """
    Creates a SES7 cluster using SLES-15-SP2
    """
    settings_dict = _gen_settings_dict('ses7', **kwargs)
    if use_deepsea:
        settings_dict['deployment_tool'] = 'deepsea'
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id')
@common_create_options
@deepsea_options
@libvirt_options
def nautilus(deployment_id, deploy, **kwargs):
    """
    Creates a Ceph Nautilus cluster using openSUSE Leap 15.1 and packages
    from filesystems:ceph:nautilus OBS project.
    """
    settings_dict = _gen_settings_dict('nautilus', **kwargs)
    _create_command(deployment_id, deploy, settings_dict)


@create.command()
@click.argument('deployment_id')
@common_create_options
@deepsea_options
@ceph_bootstrap_options
@libvirt_options
@click.option("--use-deepsea/--use-orchestrator", default=False,
              help="Use deepsea to deploy Ceph Octopus instead of SSH orchestrator")
def octopus(deployment_id, deploy, use_deepsea, **kwargs):
    """
    Creates a Ceph Octopus cluster using openSUSE Leap 15.2 and packages
    from filesystems:ceph:octopus OBS project.
    """
    settings_dict = _gen_settings_dict('octopus', **kwargs)
    if use_deepsea:
        settings_dict['deployment_tool'] = 'deepsea'
    _create_command(deployment_id, deploy, settings_dict)


@cli.command()
@click.argument('deployment_id')
@click.option('--force', is_flag=True, callback=_abort_if_false, expose_value=False,
              help='Allow to destroy the deployment without user confirmation',
              prompt='Are you sure you want to destroy the cluster?')
def destroy(deployment_id):
    """
    Destroys the deployment named DEPLOYMENT_ID by destroying the VMs and deletes the
    deployment directory.
    """
    dep = seslib.Deployment.load(deployment_id)
    dep.destroy(_print_log)


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def ssh(deployment_id, node=None):
    """
    Opens an SSH shell to node NODE in deployment DEPLOYMENT_ID.
    If the node is not specified, an SSH shell is opened on the "admin" node.
    """
    dep = seslib.Deployment.load(deployment_id)
    dep.ssh(node if node else 'admin')


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def stop(deployment_id, node=None):
    """
    Stops the VMs of the deployment DEPLOYMENT_ID.
    """
    dep = seslib.Deployment.load(deployment_id)
    dep.stop(_print_log, node)


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def start(deployment_id, node=None):
    """
    Starts the VMs of the deployment DEPLOYMENT_ID.

    If cluster was not yet deployed (if was created with the --no-deploy flag), it will
    start the deployment of the cluster.
    """
    dep = seslib.Deployment.load(deployment_id)
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
@click.option('--force', is_flag=True, callback=_abort_if_false, expose_value=False,
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
@click.argument('service', type=click.Choice(['dashboard', 'grafana', 'openattic', 'suma']),
                required=False)
@click.option('--node', default='admin', type=str, show_default=True,
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
    sesdev_main()
