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
from .exceptions import DeploymentDoesNotExists, VersionOSNotSupported, SettingTypeError, \
                        VagrantBoxDoesNotExist, NodeDoesNotExist, NoSourcePortForPortForwarding, \
                        ServicePortForwardingNotSupported, DeploymentAlreadyExists, \
                        ServiceNotFound, ExclusiveRoles, RoleNotSupported


METADATA_FILENAME = ".metadata"


logger = logging.getLogger(__name__)

JINJA_ENV = Environment(loader=PackageLoader('seslib', 'templates'), trim_blocks=True)


class GlobalSettings():
    WORKING_DIR = os.path.join(Path.home(), '.sesdev')
    CONFIG_FILE = os.path.join(WORKING_DIR, 'config.yaml')

    @classmethod
    def init(cls, working_dir):
        cls.WORKING_DIR = working_dir
        os.makedirs(cls.WORKING_DIR, exist_ok=True)


OS_BOX_MAPPING = {
    'leap-15.1': 'https://download.opensuse.org/repositories/Virtualization:/Appliances:/Images:/'
                 'openSUSE-Leap-15.1/images/Leap-15.1.x86_64-libvirt.box',
    'tumbleweed': 'https://download.opensuse.org/repositories/Virtualization:/Appliances:/Images:/'
                  'openSUSE-Tumbleweed/openSUSE_Tumbleweed/Tumbleweed.x86_64-libvirt.box',
    'sles-15-sp1': 'http://download.suse.de/ibs/Virtualization:/Vagrant:/SLE-15-SP1/images/'
                   'SLES15-SP1-Vagrant.x86_64-libvirt.box',
    'sles-12-sp3': 'http://download.suse.de/ibs/Devel:/Storage:/5.0/vagrant/sle12sp3.x86_64.box',
    'leap-15.2': 'https://download.opensuse.org/repositories/Virtualization:/Appliances:/Images:/'
                 'openSUSE-Leap-15.2/images/Leap-15.2.x86_64-libvirt.box',
    'sles-15-sp2': 'http://download.suse.de/ibs/Virtualization:/Vagrant:/SLE-15-SP2/images/'
                   'SLES15-SP2-Vagrant.x86_64-libvirt.box',
}

OS_REPOS = {
    'sles-12-sp3': {
        'base': 'http://dist.suse.de/ibs/SUSE/Products/SLE-SERVER/12-SP3/x86_64/product/',
        'update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-SERVER/12-SP3/x86_64/update/',
        'storage': 'http://dist.suse.de/ibs/SUSE/Products/Storage/5/x86_64/product/',
        'storage-update': 'http://dist.suse.de/ibs/SUSE/Updates/Storage/5/x86_64/update/'
    },
    'sles-15-sp1': {
        'base': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP1/x86_64/'
                'product/',
        'update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP1/x86_64/'
                  'update/',
        'server-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Server-Applications/'
                       '15-SP1/x86_64/product/',
        'server-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                              'SLE-Module-Server-Applications/15-SP1/x86_64/update/',
        'dev-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Development-Tools/'
                    '15-SP1/x86_64/product/',
        'dev-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Development-Tools/'
                           '15-SP1/x86_64/update/',
        'storage': 'http://download.suse.de/ibs/SUSE/Products/Storage/6/x86_64/product/',
        'storage-update': 'http://download.suse.de/ibs/SUSE/Updates/Storage/6/x86_64/update/'
    },
    'sles-15-sp2': {
        'base': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/'
                'product/',
        'update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP2/x86_64/'
                  'update/',
        'server-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Server-Applications/'
                       '15-SP2/x86_64/product/',
        'server-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                              'SLE-Module-Server-Applications/15-SP2/x86_64/update/',
        'dev-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Development-Tools/'
                    '15-SP2/x86_64/product/',
        'dev-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Development-Tools/'
                           '15-SP2/x86_64/update/',
        'container-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Containers/15-SP2/'
                          'x86_64/product/',
        'container-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Containers/'
                                 '15-SP2/x86_64/update/'
    },
}

VERSION_PREFERRED_OS = {
    'ses5': 'sles-12-sp3',
    'ses6': 'sles-15-sp1',
    'ses7': 'sles-15-sp2',
    'nautilus': 'leap-15.1',
    'octopus': 'leap-15.2',
}

VERSION_PREFERRED_DEPLOYMENT_TOOL = {
    'ses5': 'deepsea',
    'ses6': 'deepsea',
    'ses7': 'orchestrator',
    'nautilus': 'deepsea',
    'octopus': 'orchestrator'
}

VERSION_OS_REPO_MAPPING = {
    'ses5': {
        'sles-12-sp3': 'http://download.suse.de/ibs/Devel:/Storage:/5.0/SLE12_SP3/',
    },
    'nautilus': {
        'leap-15.1':  'https://download.opensuse.org/repositories/filesystems:/ceph:/nautilus/'
                      'openSUSE_Leap_15.1/',
        'tumbleweed': 'https://download.opensuse.org/repositories/filesystems:/ceph:/nautilus/'
                      'openSUSE_Tumbleweed',
    },
    'ses6': {
        'sles-15-sp1': 'http://download.suse.de/ibs/Devel:/Storage:/6.0/SLE_15_SP1/',
    },
    'octopus': {
        'leap-15.1': 'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/'
                     'openSUSE_Leap_15.1',
        'leap-15.2': 'https://download.opensuse.org/repositories/filesystems:/ceph:/master:/'
                     'upstream/openSUSE_Leap_15.2',
        'tumbleweed': 'https://download.opensuse.org/repositories/filesystems:/ceph:/master:/'
                      'upstream/openSUSE_Tumbleweed',
    },
    'ses7': {
        'sles-15-sp2': 'https://download.opensuse.org/repositories/filesystems:/ceph:/master:/'
                       'upstream/SLE_15_SP2'
    }
}


SETTINGS = {
    'version': {
        'type': str,
        'help': 'SES version to install (nautilus, octopus, ses5, ses6, ses7)',
        'default': 'nautilus'
    },
    'os': {
        'type': str,
        'help': 'openSUSE OS version (leap-15.1, tumbleweed, sles-12-sp3, or sles-15-sp1)',
        'default': None
    },
    'vagrant_box': {
        'type': str,
        'help': 'Vagrant box to use in deployment',
        'default': None
    },
    'vm_engine': {
        'type': str,
        'help': 'VM engine to use for VM deployment. Current options [libvirt]',
        'default': 'libvirt'
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
    'libvirt_use_ssh': {
        'type': bool,
        'help': 'Flag to control the use of SSH when connecting to the libvirt host',
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
        'default': [["admin", "client", "prometheus", "grafana", "openattic"],
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
    'deployment_tool': {
        'type': str,
        'help': 'Deployment tool to deploy the Ceph cluster. Currently only deepsea is supported',
        'default': None
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
        'type': int,
        'help': 'Stop deployment before running the specified DeepSea stage',
        'default': None
    },
    'repos': {
        'type': list,
        'help': 'Custom repos dictionary to apply to all nodes',
        'default': []
    },
    'repo_priority': {
        'type': bool,
        'help': 'Automatically set priority on custom zypper repos',
        'default': True
    },
    'scc_username': {
        'type': str,
        'help': 'SCC organization username',
        'default': None
    },
    'scc_password': {
        'type': str,
        'help': 'SCC organization password',
        'default': None
    },
}


class Settings():
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
                logger.warning("Setting '%s' is not known", k)
                continue
            if v is not None and not isinstance(v, SETTINGS[k]['type']):
                logger.error("Setting '%s' value has wrong type: expected %s but got %s", k,
                             SETTINGS[k]['type'], type(v))
                raise SettingTypeError(k, SETTINGS[k]['type'], v)
            setattr(self, k, v)

    @staticmethod
    def _load_config_file():
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
    def default(self, o):
        return {k: getattr(o, k) for k in SETTINGS}


class Disk():
    def __init__(self, size):
        self.size = size


class ZypperRepo():
    def __init__(self, name, url, priority=None):
        self.name = name
        self.url = url
        self.priority = priority


class Node():
    _repo_lowest_prio = 94

    def __init__(self, name, fqdn, roles, public_address, cluster_address=None, storage_disks=None,
                 ram=None, cpus=None, repo_priority=None):
        self.name = name
        self.fqdn = fqdn
        self.roles = roles
        self.public_address = public_address
        self.cluster_address = cluster_address
        if storage_disks is None:
            storage_disks = []
        self.storage_disks = storage_disks
        self.ram = ram
        self.cpus = cpus
        self.status = None
        self.repos = []
        self.repo_priority = repo_priority

    def has_role(self, role):
        return role in self.roles

    def add_repo(self, repo):
        if self.repo_priority:
            if repo.priority is None:
                repo.priority = self._repo_lowest_prio - len(self.repos)
        else:
            repo.priority = None
        self.repos.append(repo)


class Deployment():
    def __init__(self, dep_id, settings):
        self.dep_id = dep_id
        self.settings = settings
        self.nodes = {}
        self.admin = None
        self.suma = None

        if self.settings.os is None:
            self.settings.os = VERSION_PREFERRED_OS[self.settings.version]

        if self.settings.deployment_tool is None:
            self.settings.deployment_tool = VERSION_PREFERRED_DEPLOYMENT_TOOL[self.settings.version]

        self._generate_networks()
        self._generate_nodes()

    @property
    def dep_dir(self):
        return os.path.join(GlobalSettings.WORKING_DIR, self.dep_id)

    def _needs_cluster_network(self):
        if len(self.settings.roles) == 1:  # there is only 1 node
            return False
        num_nodes_with_storage = 0
        for node in self.settings.roles:
            if 'storage' in node:
                num_nodes_with_storage += 1
        if num_nodes_with_storage > 1:  # at least 2 nodes have storage
            return True
        return False

    def has_suma(self):
        for roles in self.settings.roles:
            if 'suma' in roles:
                return True
        return False

    def _generate_networks(self):
        if self._needs_cluster_network() and self.settings.public_network is not None \
                and self.settings.cluster_network is not None:
            return
        if not self._needs_cluster_network() and self.settings.public_network is not None:
            return

        deps = self.list()
        existing_networks = [dep.settings.public_network for dep in deps
                             if dep.settings.public_network]

        public_network = self.settings.public_network
        while True:
            if public_network is None or public_network in existing_networks:
                public_network = "10.20.{}.".format(random.randint(2, 200))
            else:
                break
        self.settings.public_network = public_network

        if self._needs_cluster_network():
            existing_networks = [dep.settings.cluster_network for dep in deps
                                 if dep.settings.cluster_network]

            cluster_network = self.settings.cluster_network
            while True:
                if cluster_network is None or cluster_network in existing_networks:
                    cluster_network = "10.21.{}.".format(random.randint(2, 200))
                else:
                    break
            self.settings.cluster_network = cluster_network

    def _generate_nodes(self):
        node_id = 1
        for node_roles in self.settings.roles:
            if 'suma' in node_roles and self.settings.version not in ['octopus']:
                raise RoleNotSupported('suma', self.settings.version)

            if 'admin' in node_roles or 'suma' in node_roles:
                name = 'admin'
                fqdn = 'admin.{}'.format(self.settings.domain.format(self.dep_id))
                public_address = '{}{}'.format(self.settings.public_network, 200)
            else:
                name = 'node{}'.format(node_id)
                fqdn = 'node{}.{}'.format(node_id, self.settings.domain.format(self.dep_id))
                public_address = '{}{}'.format(self.settings.public_network, 200 + node_id)
                node_id += 1

            if self.settings.version != 'ses5':
                node_roles = [r for r in node_roles if r != 'openattic']
            else:
                node_roles = [r for r in node_roles if r not in ['grafana', 'prometheus']]

            node = Node(name, fqdn, node_roles, public_address, ram=self.settings.ram * 2**10,
                        cpus=self.settings.cpus, repo_priority=self.settings.repo_priority)

            if 'admin' in node_roles:
                self.admin = node

            if 'suma' in node_roles:
                self.suma = node

            if 'storage' in node_roles:
                if self.settings.cluster_network:
                    node.cluster_address = '{}{}'.format(self.settings.cluster_network,
                                                         200 + node_id)
                for _ in range(self.settings.num_disks):
                    node.storage_disks.append(Disk(self.settings.disk_size))

            if self.has_suma():  # if suma is deployed, we need to add client-tools to all nodes
                node.add_repo(ZypperRepo(
                    'suma_client_tools',
                    'https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master:/'
                    'openSUSE_Leap_15-Uyuni-Client-Tools/openSUSE_Leap_15.0/'))

            # from https://www.uyuni-project.org/uyuni-docs/uyuni/installation/install-vm.html
            if 'suma' in node_roles:
                if self.settings.ram < 4:
                    node.ram = 4096
                if self.settings.cpus < 4:
                    node.cpus = 4
                # disk for /var/spacewalk
                node.storage_disks.append(Disk(101))
                # disk for /var/lib/pgsql
                node.storage_disks.append(Disk(51))

                node.add_repo(ZypperRepo(
                    'suma_media1',
                    'https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master/'
                    'images-openSUSE_Leap_15.1/repo/Uyuni-Server-POOL-x86_64-Media1/'))

            r_name = 'custom-repo-{}'
            for idx, repo_url in enumerate(self.settings.repos):
                node.add_repo(ZypperRepo(r_name.format(idx+1), repo_url))

            self.nodes[node.name] = node

        if self.admin and self.suma:
            raise ExclusiveRoles('admin', 'suma')

    def generate_vagrantfile(self):
        num_osds = len([n for n in self.nodes.values() if 'storage' in n.roles]) \
                   * self.settings.num_disks

        vagrant_box = self.settings.os

        try:
            version_repo = VERSION_OS_REPO_MAPPING[self.settings.version][self.settings.os]
        except KeyError:
            raise VersionOSNotSupported(self.settings.version, self.settings.os)

        if self.settings.os in OS_REPOS:
            os_base_repos = list(OS_REPOS[self.settings.os].items())
        else:
            os_base_repos = []

        template = JINJA_ENV.get_template('Vagrantfile.j2')
        return template.render(**{
            'dep_id': self.dep_id,
            'vm_engine': self.settings.vm_engine,
            'libvirt_host': self.settings.libvirt_host,
            'libvirt_user': self.settings.libvirt_user,
            'libvirt_use_ssh': 'true' if self.settings.libvirt_use_ssh else 'false',
            'libvirt_storage_pool': self.settings.libvirt_storage_pool,
            'vagrant_box': vagrant_box,
            'nodes': [n for _, n in self.nodes.items()],
            'admin': self.admin,
            'suma': self.suma,
            'deepsea_git_repo': self.settings.deepsea_git_repo,
            'deepsea_git_branch': self.settings.deepsea_git_branch,
            'version': self.settings.version,
            'use_deepsea_cli': self.settings.use_deepsea_cli,
            'stop_before_stage': self.settings.stop_before_stage,
            'num_osds': num_osds,
            'deployment_tool': self.settings.deployment_tool,
            'version_repo': version_repo,
            'os_base_repos': os_base_repos,
            'repo_priority': self.settings.repo_priority,
            'scc_username': self.settings.scc_username,
            'scc_password': self.settings.scc_password,
        })

    def save(self):
        vagrant_file = self.generate_vagrantfile()
        key = RSA.generate(2048)
        private_key = key.exportKey('PEM')
        public_key = key.publickey().exportKey('OpenSSH')

        os.makedirs(self.dep_dir, exist_ok=False)
        metadata_file = os.path.join(self.dep_dir, METADATA_FILENAME)
        with open(metadata_file, 'w') as file:
            json.dump({
                'id': self.dep_id,
                'settings': self.settings
            }, file, cls=SettingsEncoder)

        vagrantfile = os.path.join(self.dep_dir, 'Vagrantfile')
        with open(vagrantfile, 'w') as file:
            file.write(vagrant_file)

        # generate ssh key pair
        keys_dir = os.path.join(self.dep_dir, 'keys')
        os.makedirs(keys_dir)

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
        if self.settings.vagrant_box:
            using_custom_box = True
            vagrant_box = self.settings.vagrant_box
        else:
            using_custom_box = False
            vagrant_box = self.settings.os

        logger.info("Checking if vagrant box is already here: %s", vagrant_box)
        found_box = False
        output = tools.run_sync(["vagrant", "box", "list"])
        lines = output.split('\n')
        for line in lines:
            if line:
                box_name = line.split()[0]
                if box_name == vagrant_box:
                    logger.info("Found vagrant box")
                    found_box = True
                    break

        if not found_box:
            if using_custom_box:
                logger.error("Vagrant box '%s' is not installed", vagrant_box)
                raise VagrantBoxDoesNotExist(vagrant_box)

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

    def _stop(self, node):
        if self.nodes[node].status != "running":
            logger.warning("Node '%s' is not running: current status '%s'", node,
                           self.nodes[node].status)
            return
        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(['echo "sleep 2 && shutdown -h now" > /root/shutdown.sh '
                        '&& chmod +x /root/shutdown.sh'])
        tools.run_sync(ssh_cmd)
        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(['nohup /root/shutdown.sh > /dev/null 2>&1 &'])
        tools.run_sync(ssh_cmd)

    def stop(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise NodeDoesNotExist(node)
        if node:
            self._stop(node)
        else:
            for _node in self.nodes:
                self._stop(_node)

    def start(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise NodeDoesNotExist(node)

        if self.settings.vm_engine == 'libvirt':
            self.get_vagrant_box(log_handler)
        self.vagrant_up(node, log_handler)

    def __str__(self):
        return self.dep_id

    def load_status(self):
        if not os.path.exists(os.path.join(self.dep_dir, '.vagrant')):
            for node in self.nodes.values():
                node.status = "not deployed"
            return

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
        result = "Deployment VMs:\n"
        for k, v in self.nodes.items():
            result += "  -- {}:\n".format(k)
            if v.status:
                result += "     - status:           {}\n".format(v.status)
            result += "     - OS:               {}\n".format(self.settings.os)
            result += "     - ses_version:      {}\n".format(self.settings.version)
            if k == 'admin':
                result += "     - deployment_tool:  {}\n".format(self.settings.deployment_tool)
            result += "     - roles:            {}\n".format(v.roles)
            if self.settings.vagrant_box:
                result += "     - vagrant_box       {}\n".format(self.settings.vagrant_box)
            result += "     - fqdn:             {}\n".format(v.fqdn)
            result += "     - public_address:   {}\n".format(v.public_address)
            if v.cluster_address:
                result += "     - cluster_address:  {}\n".format(v.cluster_address)
            result += "     - cpus:             {}\n".format(v.cpus)
            result += "     - ram:              {}G\n".format(int(v.ram / (2 ** 10)))
            if v.storage_disks:
                result += "     - storage_disks:    {}\n".format(len(v.storage_disks))
                dev_letter = ord('b')
                for disk in v.storage_disks:
                    result += "       - /dev/vd{}        {}G\n".format(str(chr(dev_letter)),
                                                                       disk.size)
                    dev_letter += 1
            result += "     - repo_priority:    {}\n".format(self.settings.repo_priority)
            if v.repos:
                result += "     - custom_repos:\n"
                for repo in v.repos:
                    result += "       - {}\n".format(repo.url)
            result += "\n"
        return result

    def _ssh_cmd(self, name):
        if name not in self.nodes:
            raise NodeDoesNotExist(name)

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

        dep_private_key = os.path.join(self.dep_dir, "keys/id_rsa")
        _cmd = ["ssh", "root@{}".format(address), "-i", dep_private_key,
                "-o", "IdentitiesOnly yes", "-o", "StrictHostKeyChecking no",
                "-o", "UserKnownHostsFile /dev/null", "-o", "PasswordAuthentication no"]
        if proxycmd is not None:
            _cmd.extend(["-o", "ProxyCommand={}".format(proxycmd)])
        return _cmd

    def ssh(self, name):
        tools.run_interactive(self._ssh_cmd(name))

    def _find_service_node(self, service):
        if service == 'grafana' and self.settings.version == 'ses5':
            return 'admin'
        nodes = [name for name, node in self.nodes.items() if service in node.roles]
        return nodes[0] if nodes else None

    def start_port_forwarding(self, service=None, node=None, remote_port=None, local_port=None,
                              local_address=None):
        if local_address is None:
            local_address = 'localhost'

        if service is not None:
            if service not in ['dashboard', 'grafana', 'openattic', 'suma']:
                raise ServicePortForwardingNotSupported(service)

            if service in ['openattic', 'grafana']:
                node = self._find_service_node(service)
                if not node:
                    raise ServiceNotFound(service)

            if service == 'openattic':
                remote_port = 80
                local_port = 8080
                service_url = 'http://{}:{}'.format(local_address, local_port)
            elif service == 'grafana':
                remote_port = 3000
                local_port = 3000
                if self.settings.version == 'ses5':
                    service_url = 'http://{}:{}'.format(local_address, local_port)
                else:
                    service_url = 'https://{}:{}'.format(local_address, local_port)
            elif service == 'dashboard':
                remote_port = 8443
                local_port = 8443
                service_url = 'https://{}:{}'.format(local_address, local_port)

                # we need to find which node has the active mgr
                ssh_cmd = self._ssh_cmd('admin')
                ssh_cmd.append("ceph mgr services | jq -r .dashboard "
                               "| sed 's!https://\\(.*\\)\\.{}:.*/!\\1!g'"
                               .format(self.settings.domain.format(self.dep_id)))
                try:
                    node = tools.run_sync(ssh_cmd)
                    node = node.strip()
                except tools.CmdException:
                    node = 'null'
                if node == 'null':
                    raise ServiceNotFound(service)

                logger.info("dashboard is running on node %s", node)
            elif service == 'suma':
                node = 'admin'
                remote_port = 443
                local_port = 8443
                service_url = 'https://{}:{}'.format(local_address, local_port)

        else:
            if node not in self.nodes:
                raise NodeDoesNotExist(node)
            if remote_port is None:
                raise NoSourcePortForPortForwarding()
            if local_port is None:
                local_port = remote_port
            service_url = '{}:{}'.format(local_address, local_port)

        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(["-M", "-S", "{}-admin-socket".format(self.dep_id), "-fNT", "-L",
                        "{}:{}:{}:{}".format(local_address, local_port, self.nodes[node].fqdn,
                                             remote_port)])
        print("You can now access the service in: {}".format(service_url))
        tools.run_sync(ssh_cmd)

    @classmethod
    def create(cls, dep_id, settings):
        dep_dir = os.path.join(GlobalSettings.WORKING_DIR, dep_id)
        if os.path.exists(dep_dir):
            raise DeploymentAlreadyExists(dep_id)

        dep = cls(dep_id, settings)
        logger.info("creating new deployment: %s", dep)
        dep.save()
        return dep

    @classmethod
    def load(cls, dep_id, load_status=True):
        dep_dir = os.path.join(GlobalSettings.WORKING_DIR, dep_id)
        if not os.path.exists(dep_dir) or not os.path.isdir(dep_dir):
            logger.debug("%s does not exist or is not a directory", dep_dir)
            raise DeploymentDoesNotExists(dep_id)
        metadata_file = os.path.join(dep_dir, METADATA_FILENAME)
        if not os.path.exists(metadata_file) or not os.path.isfile(metadata_file):
            logger.debug("metadata file %s does not exist or is not a file", metadata_file)
            raise DeploymentDoesNotExists(dep_id)

        with open(metadata_file, 'r') as file:
            metadata = json.load(file)

        dep = cls(metadata['id'], Settings(**metadata['settings']))
        if load_status:
            dep.load_status()
        return dep

    @classmethod
    def list(cls, load_status=False):
        deps = []
        if not os.path.exists(GlobalSettings.WORKING_DIR):
            return deps
        for dep_id in os.listdir(GlobalSettings.WORKING_DIR):
            try:
                deps.append(Deployment.load(dep_id, load_status))
            except DeploymentDoesNotExists:
                continue
        return deps
