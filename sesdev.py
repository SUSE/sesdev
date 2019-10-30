import logging
import sys

import click
import pkg_resources
import seslib


logger = logging.getLogger(__name__)


@click.group()
@click.option('-w', '--work-path', required=False,
              type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help='Filesystem path to store deployments')
@click.option('-c', '--config-file', required=False,
              type=click.Path(exists=True, dir_okay=False, file_okay=True),
              help='Configuration file location')
@click.option('--debug/--no-debug', default=False)
@click.option('--log-file', type=str, default='ses-dev.log')
@click.version_option(pkg_resources.get_distribution('sesdev'), message="%(version)s")
def cli(work_path=None, config_file=None, debug=False, log_file=None):
    logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                        filename=log_file, filemode='w',
                        level=logging.INFO if not debug else logging.DEBUG)

    if work_path:
        logger.info("Working path: %s", work_path)
        seslib.GlobalSettings.WORKING_DIR = work_path

    if config_file:
        logger.info("Config file: %s", config_file)
        seslib.GlobalSettings.CONFIG_FILE = config_file


@cli.command()
def list():
    deps = seslib.list_deployments()
    for dep in deps:
        click.echo(dep.status())
        click.echo()


def _print_log(output):
    sys.stdout.write(output)
    sys.stdout.flush()


@cli.command()
@click.argument('deployment_id')
@click.option('--roles', type=str, default=None,
              help='List of roles for each node. Example for two nodes: '
                   '[admin, client, prometheus],[storage, mon, mgr]')
@click.option('--os', type=str, default=None,
              help='openSUSE OS version (leap-15.1, tumbleweed, sles-12-sp3, or sles-15-sp1)')
@click.option('--deploy/--no-deploy', default=True,
              help="Don't run the deployment phase. Just generated the Vagrantfile")
@click.option('--num-disks', default=None, type=int,
              help='Number of storage disks in OSD nodes')
@click.option('--single-node/--no-single-node', default=False,
              help='Deploy a single node cluster. Overrides --roles')
@click.option('--deepsea-cli/--salt-run', default=True,
              help="Use deepsea-cli or salt-run to execute DeepSea stages")
@click.option('--libvirt-host', type=str, default=None,
              help='Hostname of the libvirt machine')
@click.option('--libvirt-user', type=str, default=None,
              help='Username for connecting to the libvirt machine')
@click.option('--libvirt-storage-pool', type=str, default=None,
              help='Libvirt storage pool')
@click.option('--stop-before-deepsea-stage', type=int, default=None,
              help='Allows to stop deployment before running the specified DeepSea stage')
def create(deployment_id, roles, os, deploy, num_disks, single_node, deepsea_cli, libvirt_host,
           libvirt_user, libvirt_storage_pool, stop_before_deepsea_stage):
    settings_dict = {}
    if not single_node and roles:
        roles = [r.strip() for r in roles.split(",")]
        _roles = []
        _node = None
        for r in roles:
            r = r.strip()
            if r.startswith('['):
                _node = []
                if r.endswith(']'):
                    r = r[:-1]
                    _node.append(r[1:])
                    _roles.append(_node)
                else:
                    _node.append(r[1:])
            elif r.endswith(']'):
                _node.append(r[:-1])
                _roles.append(_node)
            else:
                _node.append(r)
        settings_dict['roles'] = _roles
    elif single_node:
        settings_dict['roles'] = [["admin", "storage", "mon", "mgr", "prometheus", "grafana", "mds",
                                  "igw", "rgw", "ganesha"]]

    if os:
        settings_dict['os'] = os

    if num_disks:
        if single_node and num_disks < 3:
            num_disks = 3
        settings_dict['num_disks'] = num_disks
    elif single_node:
        settings_dict['num_disks'] = 3

    if libvirt_host:
        settings_dict['libvirt_host'] = libvirt_host

    if libvirt_user:
        settings_dict['libvirt_user'] = libvirt_user

    if libvirt_storage_pool:
        settings_dict['libvirt_storage_pool'] = libvirt_storage_pool

    if deepsea_cli is not None:
        settings_dict['use_deepsea_cli'] = deepsea_cli

    if stop_before_deepsea_stage is not None:
        settings_dict['stop_before_stage'] = stop_before_deepsea_stage

    settings = seslib.Settings(**settings_dict)

    dep = seslib.Deployment.create(deployment_id, settings)
    if deploy:
        dep.start(_print_log)


@cli.command()
@click.argument('deployment_id')
def destroy(deployment_id):
    dep = seslib.Deployment.load(deployment_id)
    dep.destroy(_print_log)


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def ssh(deployment_id, node=None):
    dep = seslib.Deployment.load(deployment_id)
    dep.ssh(node if node else 'admin')


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def stop(deployment_id, node=None):
    dep = seslib.Deployment.load(deployment_id)
    dep.stop(_print_log, node)


@cli.command()
@click.argument('deployment_id')
@click.argument('node', required=False)
def start(deployment_id, node=None):
    dep = seslib.Deployment.load(deployment_id)
    dep.start(_print_log, node)


@cli.command()
@click.argument('deployment_id')
def info(deployment_id):
    dep = seslib.Deployment.load(deployment_id)
    click.echo(dep.status())


@cli.command()
@click.argument('deployment_id')
def redeploy(deployment_id):
    dep = seslib.Deployment.load(deployment_id)
    dep.destroy(_print_log)
    dep = seslib.Deployment.create(deployment_id, dep.settings)
    dep.start(_print_log)


@cli.command()
@click.argument('deployment_id')
@click.argument('service', type=click.Choice(['dashboard', 'grafana']))
def tunnel(deployment_id, service):
    click.echo("Opening tunnel to service '{}'...".format(service))
    dep = seslib.Deployment.load(deployment_id)
    dep.start_port_forwarding(service)


if __name__ == '__main__':
    # pylint: disable=unexpected-keyword-arg
    cli(prog_name='sesdev')