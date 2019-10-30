from datetime import datetime
import json
from json import JSONEncoder
import logging
import os
from pathlib import Path
import random
import shutil
import yaml

from Cryptodome.PublicKey import RSA

from jinja2 import Environment, PackageLoader, select_autoescape

from . import tools


METADATA_FILENAME = ".metadata"


logger = logging.getLogger(__name__)

jinja_env = Environment(loader=PackageLoader('seslib', 'templates'), trim_blocks=True)


class GlobalSettings(object):
    WORKING_DIR = os.path.join(Path.home(), '.sesdev')
    CONFIG_FILE = os.path.join(WORKING_DIR, 'config.yaml')

    @classmethod
    def init(cls, working_dir):
        cls.WORKING_DIR = working_dir
        os.makedirs(cls.WORKING_DIR, exist_ok=True)


OS_BOX_MAPPING = {
    'leap-15.1': 'https://download.opensuse.org/repositories/Virtualization:/Appliances:/Images:/openSUSE-Leap-15.1/images/Leap-15.1.x86_64-libvirt.box',
    'tumbleweed': 'https://download.opensuse.org/repositories/Virtualization:/Appliances:/Images:/openSUSE-Tumbleweed/openSUSE_Tumbleweed/Tumbleweed.x86_64-libvirt.box',
    'sles-15-sp1': 'http://download.suse.de/ibs/Virtualization:/Vagrant:/SLE-15-SP1/images/boxes/SLES15-SP1-Vagrant.x86_64.json',
    'sles-12-sp3': 'http://download.suse.de/ibs/Devel:/Storage:/5.0/vagrant/sle12sp3.x86_64.box',
}


SETTINGS = {
    'version': {
        'type': str,
        'help': 'SES version to install (ses5, ses6, luminous, nautilus, octopus)',
        'default': 'nautilus'
    },
    'os': {
        'type': str,
        'help': 'openSUSE OS version (leap-15.1, tumbleweed, sles-12-sp3, or sles-15-sp1)',
        'default': 'leap-15.1'
    },
    'libvirt_host': {
        'type': str,
        'help': 'Hostname/IP address of the libvirt host',
        'default': None
    },
    'libvirt_user': {
        'type': str,
        'help': 'Username to use to login into the libvirt host',
        'default': None
    },
    'libvirt_use_ssl': {
        'type': bool,
        'help': 'Flag to control the use of SSL when connecting to the libvirt host',
        'default': None
    },
    'libvirt_storage_pool': {
        'type': str,
        'help': 'The libvirt storage pool to use for creating VMs',
        'default': None
    },
    'ram': {
        'type': int,
        'help': 'RAM size in gigabytes for each node',
        'default': 4
    },
    'cpus': {
        'type': int,
        'help': 'Number of virtual CPUs in each node',
        'default': 2
    },
    'num_disks': {
        'type': int,
        'help': 'Number of additional disks in storage nodes',
        'default': 2
    },
    'disk_size': {
        'type': int,
        'help': 'Storage disk size in gigabytes',
        'default': 8
    },
    'roles': {
        'type': list,
        'help': 'List of roles for each node. Example for two nodes: '
                '[["admin", "client", "prometheus"], ["storage", "mon", "mgr"]]',
        'default': [["admin", "client", "prometheus", "grafana"],
                    ["storage", "mon", "mgr", "rgw", "igw"],
                    ["storage", "mon", "mgr", "mds", "igw", "ganesha"],
                    ["storage", "mon", "mds", "rgw", "ganesha"]]
    },
    'public_network': {
        'type': str,
        'help': 'The network address prefix for the public network',
        'default': None
    },
    'cluster_network': {
        'type': str,
        'help': 'The network address prefix for the cluster network',
        'default': None
    },
    'domain': {
        'type': str,
        'help': 'The domain name for nodes',
        'default': '{}.com'
    },
    'deepsea_git_repo': {
        'type': str,
        'help': 'If set, it will install DeepSea from this git repo',
        'default': None
    },
    'deepsea_git_branch': {
        'type': str,
        'help': 'Git branch to use',
        'default': 'master'
    },
    'use_deepsea_cli': {
        'type': bool,
        'help': 'Use deepsea-cli to run deepsea stages',
        'default': True
    },
    'stop_before_stage': {
        'type': bool,
        'help': 'Stop deployment before running the specified DeepSea stage',
        'default': None
    }
}

class Settings(object):
    # pylint: disable=no-member
    def __init__(self, **kwargs):
        config = self._load_config_file()

        self._apply_settings(config)
        self._apply_settings(kwargs)

        for k, v in SETTINGS.items():
            if k not in kwargs and k not in config:
                setattr(self, k, v['default'])

    def _apply_settings(self, settings_dict):
        for k, v in settings_dict.items():
            if k not in SETTINGS:
                logger.error("Setting '%s' is not known", k)
                raise Exception("Unknown setting: {}".format(k))
            if v is not None and not isinstance(v, SETTINGS[k]['type']):
                logger.error("Setting '%s' value has wrong type: expected %s but got %s", k,
                             SETTINGS[k]['type'], type(v))
                raise Exception("Wrong value type for setting: {}".format(k))
            setattr(self, k, v)

    def _load_config_file(self):
        if not os.path.exists(GlobalSettings.CONFIG_FILE) \
                or not os.path.isfile(GlobalSettings.CONFIG_FILE):
            return {}

        with open(GlobalSettings.CONFIG_FILE, 'r') as file:
            try:
                return yaml.load(file, Loader=yaml.FullLoader)
            except AttributeError:  # older versions of pyyaml does not have FullLoader
                return yaml.load(file)


class SettingsEncoder(JSONEncoder):
    # pylint: disable=method-hidden
    def default(self, settings):
        return {k: getattr(settings, k) for k in SETTINGS}


class Disk(object):
    def __init__(self, size):
        self.size = size


class Node(object):
    def __init__(self, name, fqdn, roles, public_address, cluster_address=None, storage_disks=None):
        self.name = name
        self.fqdn = fqdn
        self.roles = roles
        self.public_address = public_address
        self.cluster_address = cluster_address
        if storage_disks is None:
            storage_disks = []
        self.storage_disks = storage_disks
        self.status = None

    def has_role(self, role):
        return role in self.roles


class Deployment(object):
    def __init__(self, dep_id, settings):
        self.dep_id = dep_id
        self.settings = settings
        self.nodes = {}
        self.admin = None

        self._generate_networks()
        self._generate_nodes()

    @property
    def dep_dir(self):
        return os.path.join(GlobalSettings.WORKING_DIR, self.dep_id)

    def _generate_networks(self):
        if self.settings.public_network is not None and self.settings.cluster_network is not None:
            return

        deps = list_deployments()
        existing_networks = [dep.settings.public_network for dep in deps
                             if dep.settings.public_network]
        existing_networks.extend([dep.settings.cluster_network for dep in deps
                                  if dep.settings.cluster_network])
        public_network = self.settings.public_network
        cluster_network = self.settings.cluster_network

        while True:
            if public_network is None or public_network in existing_networks:
                public_network = "10.20.{}.".format(random.randint(2, 200))
            else:
                break

        while True:
            if cluster_network is None or cluster_network in existing_networks:
                cluster_network = "10.21.{}.".format(random.randint(2, 200))
            else:
                break

        self.settings.public_network = public_network
        self.settings.cluster_network = cluster_network

    def _generate_nodes(self):
        node_id = 1
        for node_roles in self.settings.roles:
            if 'admin' in node_roles:
                name = 'admin'
                fqdn = 'admin.{}'.format(self.settings.domain.format(self.dep_id))
                public_address = '{}{}'.format(self.settings.public_network, 200)
            else:
                name = 'node{}'.format(node_id)
                fqdn = 'node{}.{}'.format(node_id, self.settings.domain.format(self.dep_id))
                public_address = '{}{}'.format(self.settings.public_network, 200 + node_id)
                node_id += 1

            node = Node(name, fqdn, node_roles, public_address)
            if 'admin' in node_roles:
                self.admin = node

            if 'storage' in node_roles:
                node.cluster_address = '{}{}'.format(self.settings.cluster_network,
                                                     200 + node_id)
                for _ in range(self.settings.num_disks):
                    node.storage_disks.append(Disk(self.settings.disk_size))

            self.nodes[node.name] = node

    def generate_vagrantfile(self):
        num_osds = len([n for n in self.nodes.values() if 'storage' in n.roles]) \
                   * self.settings.num_disks


        template = jinja_env.get_template('Vagrantfile.j2')
        return template.render(**{
            'libvirt_host': self.settings.libvirt_host,
            'libvirt_user': self.settings.libvirt_user,
            'libvirt_use_ssl': 'true' if self.settings.libvirt_use_ssl else 'false',
            'libvirt_storage_pool': self.settings.libvirt_storage_pool,
            'ram': self.settings.ram * 2**10,
            'cpus': self.settings.cpus,
            'vagrant_box': self.settings.os,
            'nodes': [n for _, n in self.nodes.items()],
            'admin': self.admin,
            'deepsea_git_repo': self.settings.deepsea_git_repo,
            'deepsea_git_branch': self.settings.deepsea_git_branch,
            'version': self.settings.version,
            'use_deepsea_cli': self.settings.use_deepsea_cli,
            'stop_before_stage': self.settings.stop_before_stage,
            'num_osds': num_osds
        })

    def _save(self):
        os.makedirs(self.dep_dir, exist_ok=False)
        metadata_file = os.path.join(self.dep_dir, METADATA_FILENAME)
        with open(metadata_file, 'w') as file:
            json.dump({
                'id': self.dep_id,
                'settings': self.settings
            }, file, cls=SettingsEncoder)

        vagrantfile = os.path.join(self.dep_dir, 'Vagrantfile')
        with open(vagrantfile, 'w') as file:
            file.write(self.generate_vagrantfile())

        # generate ssh key pair
        keys_dir = os.path.join(self.dep_dir, 'keys')
        os.makedirs(keys_dir)
        key = RSA.generate(2048)
        private_key = key.export_key('PEM')
        public_key = key.publickey().export_key('OpenSSH')

        with open(os.path.join(keys_dir, 'id_rsa'), 'w') as file:
            file.write(private_key.decode('utf-8'))
        os.chmod(os.path.join(keys_dir, 'id_rsa'), 0o600)

        with open(os.path.join(keys_dir, 'id_rsa.pub'), 'w') as file:
            file.write(public_key.decode('utf-8'))
        os.chmod(os.path.join(keys_dir, 'id_rsa.pub'), 0o600)

        # bin dir with helper scripts
        bin_dir = os.path.join(self.dep_dir, 'bin')
        os.makedirs(bin_dir)

    def get_vagrant_box(self, log_handler):
        logger.info("Checking if vagrant box is already here: %s", self.settings.os)
        found_box = False
        output = tools.run_sync(["vagrant", "box", "list"])
        lines = output.split('\n')
        for line in lines:
            if line:
                box_name = line.split()[0]
                if box_name == self.settings.os:
                    logger.info("Found vagrant box")
                    found_box = True
                    break

        if not found_box:
            logger.info("Vagrant box for '%s' is not installed, we need to add it",
                        self.settings.os)

            log_handler("Downloading vagrant box: {}\n".format(self.settings.os))

            tools.run_async(["vagrant", "box", "add", "--provider", "libvirt", "--name",
                             self.settings.os, OS_BOX_MAPPING[self.settings.os]], log_handler)

    def vagrant_up(self, node, log_handler):
        cmd = ["vagrant", "up"]
        if node is not None:
            cmd.append(node)
        tools.run_async(cmd, log_handler, self.dep_dir)

    def destroy(self, log_handler):
        for node in self.nodes.values():
            if node.status == 'not deployed':
                continue
            tools.run_async(["vagrant", "destroy", node.name, "--force"], log_handler, self.dep_dir)
        shutil.rmtree(self.dep_dir)

    def _stop(self, node, log_handler):
        if self.nodes[node].status != "running":
            logger.warning("Node '%s' is not running: current status '%s'", node,
                           self.nodes[node].status)
            return
        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(['echo "sleep 2 && shutdown -h now" > /root/shutdown.sh && chmod +x /root/shutdown.sh'])
        tools.run_sync(ssh_cmd)
        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(['nohup /root/shutdown.sh > /dev/null 2>&1 &'])
        tools.run_sync(ssh_cmd)

    def stop(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise Exception("Node '{}' does not exist in this deployment".format(node))
        elif node:
            self._stop(node, log_handler)
        else:
            for node in self.nodes:
                self._stop(node, log_handler)

    def start(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise Exception("Node '{}' does not exist in this deployment".format(node))

        self.get_vagrant_box(log_handler)
        self.vagrant_up(node, log_handler)

    def __str__(self):
        return self.dep_id

    def _load_status(self):
        out = tools.run_sync(["vagrant", "status"], cwd=self.dep_dir)
        for line in [line.strip() for line in out.split('\n')]:
            if line:
                line_arr = line.split(' ', 1)
                if line_arr[0] in self.nodes:
                    if line_arr[1].strip().startswith("running"):
                        self.nodes[line_arr[0]].status = "running"
                    elif line_arr[1].strip().startswith("not created"):
                        self.nodes[line_arr[0]].status = "not deployed"
                    elif line_arr[1].strip().startswith("shutoff"):
                        self.nodes[line_arr[0]].status = "stopped"
                    elif line_arr[1].strip().startswith("paused"):
                        self.nodes[line_arr[0]].status = "suspended"

    def status(self):
        result = "{}:\n".format(self.dep_id)
        for k, v in self.nodes.items():
            result += "  - {}: {}\t{}\n".format(k, v.roles, v.status)
        return result

    def _ssh_cmd(self, name):
        if name not in self.nodes:
            raise Exception("Node '{}' does not exist in this deployment".format(name))

        out = tools.run_sync(["vagrant", "ssh-config", name], cwd=self.dep_dir)
        address = None
        proxycmd = None
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('HostName'):
                address = line[len('HostName')+1:]
            elif line.startswith('ProxyCommand'):
                proxycmd = line[len('ProxyCommand')+1:]

        if address is None:
            raise Exception("Could not get HostName info from 'vagrant ssh-config {}' command"
                            .format(name))
        if proxycmd is None:
            raise Exception("Could not get ProxyCommand info from 'vagrant ssh-config {}' command"
                            .format(name))

        dep_private_key = os.path.join(self.dep_dir, "keys/id_rsa")
        return ["ssh", "root@{}".format(address), "-i", dep_private_key,
                "-o", "IdentitiesOnly yes", "-o", "StrictHostKeyChecking no",
                "-o", "UserKnownHostsFile /dev/null", "-o", "PasswordAuthentication no",
                "-o", "ProxyCommand={}".format(proxycmd)]

    def ssh(self, name):
        tools.run_interactive(self._ssh_cmd(name))

    def start_port_forwarding(self, service):
        ssh_cmd = self._ssh_cmd('admin')
        if service == 'dashboard':
            port = 8443
        elif service == 'grafana':
            port = 3000
        else:
            raise Exception("Service '{}' not supported".format(service))

        ssh_cmd.extend(["-M", "-S", "{}-admin-socket".format(self.dep_id), "-fNT", "-L",
                        "{}:{}:{}".format(port, self.nodes['admin'].fqdn, port)])
        print("You can now access '{}' in: https://localhost:{}".format(service, port))
        tools.run_sync(ssh_cmd)

    @classmethod
    def create(cls, dep_id, settings):
        dep = cls(dep_id, settings)
        logger.info("creating new deployment: %s", dep)
        dep._save()
        return dep

    @classmethod
    def load(cls, dep_id):
        dep_dir = os.path.join(GlobalSettings.WORKING_DIR, dep_id)
        if not os.path.exists(dep_dir) or not os.path.isdir(dep_dir):
            logger.debug("%s does not exist or is not a directory", dep_dir)
            return None
        metadata_file = os.path.join(dep_dir, METADATA_FILENAME)
        if not os.path.exists(metadata_file) or not os.path.isfile(metadata_file):
            logger.debug("metadata file %s does not exist or is not a file", metadata_file)
            return None

        with open(metadata_file, 'r') as file:
            metadata = json.load(file)

        dep = cls(metadata['id'], Settings(**metadata['settings']))
        dep._load_status()
        return dep


def list_deployments():
    """
    List the available deployments
    """
    deps = []
    if not os.path.exists(GlobalSettings.WORKING_DIR):
        return deps
    for dep_id in os.listdir(GlobalSettings.WORKING_DIR):
        dep = Deployment.load(dep_id)
        if dep:
            deps.append(dep)
    return deps
