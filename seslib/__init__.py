import json
import logging
import os
from pathlib import Path
import random
import re
import shutil
from xml.dom import minidom
import yaml

from Cryptodome.PublicKey import RSA
from jinja2 import Environment, PackageLoader

import libvirt

from . import tools
from .exceptions import DeploymentDoesNotExists, VersionOSNotSupported, SettingTypeError, \
                        VagrantBoxDoesNotExist, NodeDoesNotExist, NoSourcePortForPortForwarding, \
                        ServicePortForwardingNotSupported, DeploymentAlreadyExists, \
                        ServiceNotFound, ExclusiveRoles, RoleNotKnown, RoleNotSupported, \
                        CmdException, VagrantSshConfigNoHostName, ScpInvalidSourceOrDestination, \
                        UniqueRoleViolation, SettingNotKnown, SupportconfigOnlyOnSLE, \
                        NoPrometheusGrafanaInSES5, BadMakeCheckRolesNodes, \
                        DuplicateRolesNotSupported, NoSupportConfigTarballFound, \
                        ExplicitAdminRoleNotAllowed, SubcommandNotSupportedInVersion, \
                        DepIDWrongLength, DepIDIllegalChars


JINJA_ENV = Environment(loader=PackageLoader('seslib', 'templates'), trim_blocks=True)
METADATA_FILENAME = ".metadata"

logger = logging.getLogger(__name__)


def _log_debug(log_msg):
    logger.debug(log_msg)


def _log_info(log_msg):
    logger.info(log_msg)


def _log_warning(log_msg):
    logger.warning(log_msg)


class GlobalSettings():
    A_WORKING_DIR = os.path.join(Path.home(), '.sesdev')
    CEPH_SALT_REPO = 'https://github.com/ceph/ceph-salt'
    CEPH_SALT_BRANCH = 'master'
    CONFIG_FILE = os.path.join(A_WORKING_DIR, 'config.yaml')
    DEBUG = False
    MAKECHECK_DEFAULT_RAM = 8
    ROLES_SINGLE_NODE_LUMINOUS = (
        "[ master, storage, mon, mgr, mds, igw, rgw, nfs, openattic ]"
        )
    ROLES_SINGLE_NODE_NAUTILUS = (
        "[ master, storage, mon, mgr, prometheus, grafana, mds, igw, rgw, "
        "nfs ]"
        )
    ROLES_SINGLE_NODE_OCTOPUS = (
        "[ master, bootstrap, storage, mon, mgr, prometheus, grafana, mds, "
        "igw, rgw, nfs ]"
        )
    SSH_KEY_NAME = 'sesdev'  # do NOT use 'id_rsa'
    VAGRANT_DEBUG = False

    @classmethod
    def init_path_to_qa(cls, full_path_to_sesdev_executable):
        if full_path_to_sesdev_executable.startswith('/usr'):
            cls.PATH_TO_QA = '/usr/share/sesdev/qa'
        else:
            cls.PATH_TO_QA = os.path.join(
                os.path.dirname(full_path_to_sesdev_executable),
                '../qa/'
                )


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
        'sdk': 'http://dist.suse.de/ibs/SUSE/Products/SLE-SDK/12-SP3/x86_64/product/',
        'sdk-update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-SDK/12-SP3/x86_64/update/',
        'storage': 'http://dist.suse.de/ibs/SUSE/Products/Storage/5/x86_64/product/',
        'storage-update': 'http://dist.suse.de/ibs/SUSE/Updates/Storage/5/x86_64/update/'
    },
    'sles-15-sp1': {
        'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP1/x86_64/product/',
        'base': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP1/x86_64/'
                'product/',
        'update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP1/x86_64/'
                  'update/',
        'server-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Server-Applications/'
                       '15-SP1/x86_64/product/',
        'server-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                              'SLE-Module-Server-Applications/15-SP1/x86_64/update/',
        'desktop-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Desktop-Applications/'
                        '15-SP1/x86_64/product/',
        'desktop-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                               'SLE-Module-Desktop-Applications/15-SP1/x86_64/update/',
        'dev-tools': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Module-Development-Tools/15-SP1/'
                     'x86_64/product/',
        'dev-tools-update': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Module-Development-Tools/'
                            '15-SP1/x86_64/product/',
        'workstation': 'http://download.suse.de/ibs/SUSE:/SLE-15-SP1:/GA:/TEST/images/repo/'
                       'SLE-15-SP1-Product-WE-POOL-x86_64-Media1/',
        'workstation-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Product-WE/15-SP1/'
                              'x86_64/update/',
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
        'desktop-apps': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Desktop-Applications/'
                        '15-SP2/x86_64/product/',
        'desktop-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                               'SLE-Module-Desktop-Applications/15-SP2/x86_64/update/',
        'dev-tools': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Development-Tools/'
                     '15-SP2/x86_64/product/',
        'dev-tools-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Development-Tools/'
                            '15-SP2/x86_64/update/',
        'workstation': 'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/GA:/TEST/images/repo/'
                       'SLE-15-SP2-Product-WE-POOL-x86_64-Media1/',
        'workstation-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Product-WE/15-SP2/'
                              'x86_64/update/',
        'storage7-media': 'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/Update:/Products:/SES7/'
                          'images/repo/SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/',
    },
}

IMAGE_PATHS = {
    'ses7': 'registry.suse.de/devel/storage/7.0/containers/ses/7/ceph/ceph',
    'octopus': 'registry.opensuse.org/filesystems/ceph/octopus/upstream/images/ceph/ceph',
    'pacific': 'registry.opensuse.org/filesystems/ceph/master/upstream/images/ceph/ceph',
}

VERSION_PREFERRED_OS = {
    'ses5': 'sles-12-sp3',
    'ses6': 'sles-15-sp1',
    'ses7': 'sles-15-sp2',
    'nautilus': 'leap-15.1',
    'octopus': 'leap-15.2',
    'pacific': 'leap-15.2',
    'caasp4': 'sles-15-sp1',
    'makecheck': 'tumbleweed',
}

VERSION_PREFERRED_DEPLOYMENT_TOOL = {
    'ses5': 'deepsea',
    'ses6': 'deepsea',
    'ses7': 'cephadm',
    'nautilus': 'deepsea',
    'octopus': 'cephadm',
    'pacific': 'cephadm',
    'caasp4': None,
    'makecheck': None,
}

KNOWN_ROLES = [
    "admin",
    "bootstrap",
    "client",
    "ganesha",       # deprecated (replaced by "nfs")
    "grafana",
    "igw",
    "loadbalancer",
    "makecheck",
    "master",
    "mds",
    "mgr",
    "mon",
    "nfs",
    "openattic",
    "prometheus",
    "rgw",
    "storage",
    "suma",
    "worker",
]

LUMINOUS_DEFAULT_ROLES = [["master", "client", "openattic"],
                          ["storage", "mon", "mgr", "rgw", "igw"],
                          ["storage", "mon", "mgr", "mds", "nfs"],
                          ["storage", "mon", "mgr", "mds", "rgw", "nfs"]]

NAUTILUS_DEFAULT_ROLES = [["master", "client", "prometheus", "grafana"],
                          ["storage", "mon", "mgr", "rgw", "igw"],
                          ["storage", "mon", "mgr", "mds", "igw", "nfs"],
                          ["storage", "mon", "mgr", "mds", "rgw", "nfs"]]

OCTOPUS_DEFAULT_ROLES = [["master", "client", "prometheus", "grafana"],
                         ["bootstrap", "storage", "mon", "mgr", "rgw", "igw"],
                         ["storage", "mon", "mgr", "mds", "igw", "nfs"],
                         ["storage", "mon", "mgr", "mds", "rgw", "nfs"]]

VERSION_DEFAULT_ROLES = {
    'ses5': LUMINOUS_DEFAULT_ROLES,
    'ses6': NAUTILUS_DEFAULT_ROLES,
    'ses7': OCTOPUS_DEFAULT_ROLES,
    'nautilus': NAUTILUS_DEFAULT_ROLES,
    'octopus': OCTOPUS_DEFAULT_ROLES,
    'pacific': OCTOPUS_DEFAULT_ROLES,
    'caasp4': [["master"], ["worker"], ["worker"], ["loadbalancer"]],
    'makecheck': [["makecheck"]],
}

VERSION_OS_REPO_MAPPING = {
    'ses5': {
        'sles-12-sp3': [
            'http://download.suse.de/ibs/Devel:/Storage:/5.0/images/repo/'
            'SUSE-Enterprise-Storage-5-POOL-x86_64-Media1/'
        ],
    },
    'nautilus': {
        'leap-15.1': [
            'https://download.opensuse.org/repositories/filesystems:/ceph:/nautilus/'
            'openSUSE_Leap_15.1/'
        ],
    },
    'ses6': {
        'sles-15-sp1': [
            'http://download.suse.de/ibs/Devel:/Storage:/6.0/images/repo/'
            'SUSE-Enterprise-Storage-6-POOL-x86_64-Media1/'
        ],
    },
    'octopus': {
        'leap-15.1': [
            'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/'
            'openSUSE_Leap_15.1'
        ],
        'leap-15.2': [
            'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/'
            'openSUSE_Leap_15.2'
        ],
        'tumbleweed': [
            'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus:/upstream/'
            'openSUSE_Tumbleweed'
        ],
    },
    'pacific': {
        'leap-15.2': [
            'https://download.opensuse.org/repositories/filesystems:/ceph:/master:/upstream/'
            'openSUSE_Leap_15.2'
        ],
        'tumbleweed': [
            'https://download.opensuse.org/repositories/filesystems:/ceph:/master:/upstream/'
            'openSUSE_Tumbleweed'
        ],
    },
    'ses7': {
        'sles-15-sp2': [
            'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/Update:/Products:/SES7/images/repo/'
            'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/',
            'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
            'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
        ],
    },
    'caasp4': {
        'sles-15-sp1': [
            'http://download.suse.de/ibs/SUSE:/SLE-15-SP1:/Update:/Products:/CASP40:/Update/'
            'standard/',
            'http://download.suse.de/ibs/SUSE:/SLE-15-SP1:/Update:/Products:/CASP40/standard/',
            'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Containers/15-SP1/x86_64/product/'
        ],
    },
    'makecheck': {
        'sles-12-sp3': [
            'http://download.suse.de/ibs/Devel:/Storage:/5.0/images/repo/'
            'SUSE-Enterprise-Storage-5-POOL-x86_64-Media1/',
            'http://download.suse.de/ibs/Devel:/Storage:/5.0/images/repo/'
            'SUSE-Enterprise-Storage-5-POOL-Internal-x86_64-Media/',
        ],
        'sles-15-sp1': [
            'http://download.suse.de/ibs/Devel:/Storage:/6.0/images/repo/'
            'SUSE-Enterprise-Storage-6-POOL-x86_64-Media1/',
            # 'http://download.suse.de/ibs/Devel:/Storage:/6.0/images/repo/'
            # 'SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Media/',
        ],
        'leap-15.1': [],
        'sles-15-sp2': [
            'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
            'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/',
            'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
            'SUSE-Enterprise-Storage-7-POOL-Internal-x86_64-Media/',
        ],
        'leap-15.2': [],
        'tumbleweed': [],
    },
}


SETTINGS = {
    # RESERVED KEY, DO NOT USE: 'strict'
    'version': {
        'type': str,
        'help': 'Deployment version to install ("nautilus", "ses6", "caasp4", etc.)',
        'default': 'nautilus',
    },
    'os': {
        'type': str,
        'help': 'openSUSE OS version (leap-15.1, tumbleweed, sles-12-sp3, or sles-15-sp1)',
        'default': '',
    },
    'os_repos': {
        'type': dict,
        'help': 'repos to add on all VMs of a given operating system (os)',
        'default': OS_REPOS,
    },
    'version_os_repo_mapping': {
        'type': dict,
        'help': 'additional repos to be added on particular VERSION:OS combinations',
        'default': VERSION_OS_REPO_MAPPING,
    },
    'image_paths': {
        'type': dict,
        'help': 'paths to container images to be passed to "podman" and "cephadm bootstrap"',
        'default': IMAGE_PATHS,
    },
    'vagrant_box': {
        'type': str,
        'help': 'Vagrant box to use in deployment',
        'default': '',
    },
    'vm_engine': {
        'type': str,
        'help': 'VM engine to use for VM deployment. Current options [libvirt]',
        'default': 'libvirt',
    },
    'libvirt_host': {
        'type': str,
        'help': 'Hostname/IP address of the libvirt host',
        'default': '',
    },
    'libvirt_user': {
        'type': str,
        'help': 'Username to use to login into the libvirt host',
        'default': '',
    },
    'libvirt_use_ssh': {
        'type': bool,
        'help': 'Flag to control the use of SSH when connecting to the libvirt host',
        'default': None,
    },
    'libvirt_private_key_file': {
        'type': str,
        'help': 'Path to SSH private key file to use when connecting to the libvirt host',
        'default': '',
    },
    'libvirt_storage_pool': {
        'type': str,
        'help': 'The libvirt storage pool to use for creating VMs',
        'default': '',
    },
    'libvirt_networks': {
        'type': str,
        'help': 'Existing libvirt networks to use (single or comma separated list)',
        'default': '',
    },
    'ram': {
        'type': int,
        'help': 'RAM size in gigabytes for each node',
        'default': 4,
    },
    'explicit_ram': {
        'type': bool,
        'help': 'Whether --ram was given on the command line',
        'default': False,
    },
    'cpus': {
        'type': int,
        'help': 'Number of virtual CPUs in each node',
        'default': 2,
    },
    'explicit_cpus': {
        'type': bool,
        'help': 'Whether --cpus was given on the command line',
        'default': False,
    },
    'single_node': {
        'type': bool,
        'help': 'Whether --single-node was given on the command line',
        'default': False,
    },
    'num_disks': {
        'type': int,
        'help': 'Number of additional disks in storage nodes',
        'default': 2,
    },
    'explicit_num_disks': {
        'type': bool,
        'help': 'Whether --num-disks was given on the command line',
        'default': False,
    },
    'disk_size': {
        'type': int,
        'help': 'Storage disk size in gigabytes',
        'default': 8,
    },
    'version_default_roles': {
        'type': dict,
        'help': 'Default roles for each node - one set of default roles per deployment version',
        'default': VERSION_DEFAULT_ROLES,
    },
    'roles': {
        'type': list,
        'help': 'Roles to apply to the current deployment',
        'default': [],
    },
    'public_network': {
        'type': str,
        'help': 'The network address prefix for the public network',
        'default': '',
    },
    'cluster_network': {
        'type': str,
        'help': 'The network address prefix for the cluster network',
        'default': '',
    },
    'domain': {
        'type': str,
        'help': 'The domain name for nodes',
        'default': '{}.test',
    },
    'non_interactive': {
        'type': bool,
        'help': 'Whether the user wants to be asked',
        'default': False,
    },
    'encrypted_osds': {
        'type': bool,
        'help': 'Whether OSDs should be deployed encrypted',
        'default': False,
    },
    'deployment_tool': {
        'type': str,
        'help': 'Deployment tool (deepsea, cephadm) to deploy the Ceph cluster',
        'default': '',
    },
    'deepsea_git_repo': {
        'type': str,
        'help': 'If set, it will install DeepSea from this git repo',
        'default': '',
    },
    'deepsea_git_branch': {
        'type': str,
        'help': 'Git branch to use',
        'default': 'master',
    },
    'stop_before_stage': {
        'type': int,
        'help': 'Stop deployment before running the specified DeepSea stage',
        'default': None,
    },
    'repos': {
        'type': list,
        'help': 'Custom repos dictionary to apply to all nodes',
        'default': [],
    },
    'repo_priority': {
        'type': bool,
        'help': 'Automatically set priority on custom zypper repos',
        'default': True,
    },
    'qa_test': {
        'type': bool,
        'help': 'Automatically run integration tests on the deployed cluster',
        'default': False,
    },
    'scc_username': {
        'type': str,
        'help': 'SCC organization username',
        'default': '',
    },
    'scc_password': {
        'type': str,
        'help': 'SCC organization password',
        'default': '',
    },
    'ceph_salt_git_repo': {
        'type': str,
        'help': 'If set, it will install ceph-salt from this git repo',
        'default': '',
    },
    'ceph_salt_git_branch': {
        'type': str,
        'help': 'ceph-salt git branch to use',
        'default': '',
    },
    'stop_before_ceph_salt_config': {
        'type': bool,
        'help': 'Stops deployment before ceph-salt config',
        'default': False,
    },
    'stop_before_ceph_salt_apply': {
        'type': bool,
        'help': 'Stops deployment before ceph-salt apply',
        'default': False,
    },
    'stop_before_ceph_orch_apply': {
        'type': bool,
        'help': 'Stops deployment before ceph orch apply',
        'default': False,
    },
    'image_path': {
        'type': str,
        'help': 'Container image path for Ceph daemons',
        'default': '',
    },
    'makecheck_ceph_repo': {
        'type': str,
        'help': 'Repo from which to clone Ceph source code',
        'default': '',
    },
    'makecheck_ceph_branch': {
        'type': str,
        'help': 'Branch to check out for purposes of running "make check"',
        'default': '',
    },
    'makecheck_username': {
        'type': str,
        'help': 'Name of ordinary user that will run make check',
        'default': 'sesdev',
    },
    'makecheck_stop_before_git_clone': {
        'type': bool,
        'help': 'Stop before cloning the git repo (make check)',
        'default': False,
    },
    'makecheck_stop_before_install_deps': {
        'type': bool,
        'help': 'Stop before running install-deps.sh (make check)',
        'default': False,
    },
    'makecheck_stop_before_run_make_check': {
        'type': bool,
        'help': 'Stop before running run-make-check.sh (make check)',
        'default': False,
    },
    'use_salt': {
        'type': bool,
        'help': 'Use "salt" (or "salt-run") to apply Salt Formula (or execute DeepSea Stages)',
        'default': False,
    },
    'caasp_deploy_ses': {
        'type': bool,
        'help': 'Deploy SES using rook in CaasP',
        'default': False,
    },
    'synced_folder': {
        'type': list,
        'help': 'Sync Folders to VM',
        'default': [],
    },
}


class Box():
    # pylint: disable=no-member
    def __init__(self, settings):
        self.libvirt_use_ssh = settings.libvirt_use_ssh
        self.libvirt_private_key_file = settings.libvirt_private_key_file
        self.libvirt_user = settings.libvirt_user
        self.libvirt_host = settings.libvirt_host
        self.libvirt_storage_pool = (
            settings.libvirt_storage_pool if settings.libvirt_storage_pool else 'default'
        )
        self.libvirt_conn = None
        self.libvirt_uri = None
        self.pool = None
        self._populate_box_list()

    def _build_libvirt_uri(self):
        uri = None
        if self.libvirt_use_ssh:
            uri = 'qemu+ssh://'
            if self.libvirt_user:
                uri += "{}@".format(self.libvirt_user)
            assert self.libvirt_host, "Cannot use qemu+ssh without a host"
            uri += "{}/system".format(self.libvirt_host)
            if self.libvirt_private_key_file:
                if '/' not in self.libvirt_private_key_file:
                    self.libvirt_private_key_file = os.path.join(
                        os.path.expanduser('~'),
                        '.ssh',
                        self.libvirt_private_key_file
                        )
                uri += '?keyfile={}'.format(self.libvirt_private_key_file)
        else:
            uri = 'qemu:///system'
        self.libvirt_uri = uri

    def _populate_box_list(self):
        self.all_possible_boxes = OS_BOX_MAPPING.keys()
        self.boxes = []
        output = tools.run_sync(["vagrant", "box", "list"])
        lines = output.split('\n')
        for line in lines:
            if 'libvirt' in line:
                box_name = line.split()[0]
                if box_name in self.all_possible_boxes:
                    self.boxes.append(box_name)

    def exists(self, box_name):
        return box_name in self.boxes

    def get_image_by_box(self, box_name):
        #
        # open connection to libvirt server
        self.open_libvirt_connection()
        #
        # verify that the corresponding image exists in libvirt storage pool
        self.pool = self.libvirt_conn.storagePoolLookupByName(self.libvirt_storage_pool)
        removal_candidates = []
        for removal_candidate in self.pool.listVolumes():
            if str(removal_candidate).startswith('{}_vagrant_box_image'.format(box_name)):
                removal_candidates.append(removal_candidate)
        if len(removal_candidates) == 0:
            return None
        if len(removal_candidates) == 1:
            return removal_candidates[0]
        #
        # bad news - multiple images match the box name
        print("Images matching Vagrant Box ->{}<-".format(box_name))
        print("===================================================")
        for candidate in removal_candidates:
            print(candidate)
        print()
        assert False, \
            (
                "Too many matching images. Don't know which one to remove. "
                "This should not happen - please raise a bug!"
            )
        return None

    def get_images_by_deployment(self, dep_id):
        self.open_libvirt_connection()
        self.pool = self.libvirt_conn.storagePoolLookupByName(self.libvirt_storage_pool)
        matching_images = []
        for removal_candidate in self.pool.listVolumes():
            if str(matching_images).startswith(dep_id):
                matching_images.append(removal_candidate)
        return matching_images

    def get_networks_by_deployment(self, dep_id):
        self.open_libvirt_connection()
        domains = [x for x in self.libvirt_conn.listAllDomains() if
                   x.name().startswith(dep_id)]

        logger.debug("libvirt matching domains: %s", domains)

        networks = set()
        for domain in domains:
            xml = minidom.parseString(domain.XMLDesc())
            sources_lst = xml.getElementsByTagName("source")

            ifaces = [source for source in sources_lst if
                      source.parentNode.nodeName == "interface" and
                      source.parentNode.hasAttribute("type") and
                      source.parentNode.getAttribute("type") == "network"]

            logger.debug("libvirt domain's interfaces: %s", ifaces)

            for iface in ifaces:
                name = iface.getAttribute("network")
                if name == "vagrant-libvirt":
                    continue
                networks.add(name)
        return list(networks)

    def list(self):
        for box in self.boxes:
            print(box)

    def open_libvirt_connection(self):
        if self.libvirt_conn:
            return None
        self._build_libvirt_uri()
        # print("Opening libvirt connection to ->{}<-".format(self.libvirt_uri))
        self.libvirt_conn = libvirt.open(self.libvirt_uri)
        return None

    def remove_image(self, image_name):
        image = self.pool.storageVolLookupByName(image_name)
        image.delete()

    @staticmethod
    def remove_box(box_name):
        tools.run_sync(["vagrant", "box", "remove", box_name])

    def destroy_network(self, name):
        self.open_libvirt_connection()

        try:
            network = self.libvirt_conn.networkLookupByName(name)
        except libvirt.libvirtError:
            logger.warning("Unable to find network '%s' for removal", name)
            return False

        try:
            network.destroy()
        except libvirt.libvirtError:
            logger.error("Something went wrong destroying network '%s'", name)
            return False

        return True


class Settings():
    # pylint: disable=no-member
    def __init__(self, strict=True, **kwargs):
        self.strict = strict
        config = self._load_config_file()

        self._apply_settings(config)
        self._apply_settings(kwargs)

        for k, v in SETTINGS.items():
            if k not in kwargs and k not in config:
                setattr(self, k, v['default'])

    def override(self, setting, new_value):
        if setting not in SETTINGS:
            raise SettingNotKnown(setting)
        _log_debug("Overriding setting '{}', old value: {}"
                   .format(setting, getattr(self, setting)))
        _log_debug("Overriding setting '{}', new value: {}"
                   .format(setting, new_value))
        setattr(self, setting, new_value)

    def _apply_settings(self, settings_dict):
        for k, v in settings_dict.items():
            if k not in SETTINGS:
                if self.strict:
                    raise SettingNotKnown(k)
                logger.warning("Setting '%s' is not known - listing a legacy cluster?", k)
                continue
            if v is not None and not isinstance(v, SETTINGS[k]['type']):
                logger.error("Setting '%s' value has wrong type: expected %s but got %s", k,
                             SETTINGS[k]['type'], type(v))
                raise SettingTypeError(k, SETTINGS[k]['type'], v)
            setattr(self, k, v)

    @staticmethod
    def _load_config_file():

        config_tree = {}

        def __fill_in_config_tree(config_param, global_param):
            """
            fill in missing parts of config_tree[config_param]
            from global_param
            """
            if config_param in config_tree:
                for k, v in global_param.items():
                    if k in config_tree[config_param]:
                        pass
                    else:
                        config_tree[config_param][k] = v

        if not os.path.exists(GlobalSettings.CONFIG_FILE) \
                or not os.path.isfile(GlobalSettings.CONFIG_FILE):
            return config_tree
        with open(GlobalSettings.CONFIG_FILE, 'r') as file:
            try:
                config_tree = yaml.load(file, Loader=yaml.FullLoader)
            except AttributeError:  # older versions of pyyaml does not have FullLoader
                config_tree = yaml.load(file)
        if not config_tree:
            config_tree = {}
        _log_debug("_load_config_file: config_tree: {}".format(config_tree))
        assert isinstance(config_tree, dict), "yaml.load() of config file misbehaved!"
        __fill_in_config_tree('os_repos', OS_REPOS)
        __fill_in_config_tree('version_os_repo_mapping', VERSION_OS_REPO_MAPPING)
        __fill_in_config_tree('image_paths', IMAGE_PATHS)
        __fill_in_config_tree('version_default_roles', VERSION_DEFAULT_ROLES)
        return config_tree


class SettingsEncoder(json.JSONEncoder):
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

    def __init__(self,
                 name,
                 fqdn,
                 roles,
                 networks,
                 public_address=None,
                 cluster_address=None,
                 storage_disks=None,
                 ram=None,
                 cpus=None,
                 repo_priority=None):
        self.name = name
        self.fqdn = fqdn
        self.roles = roles
        self.networks = networks
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
        if role not in KNOWN_ROLES:
            raise RoleNotKnown(role)
        return role in self.roles

    def has_roles(self):
        _log_debug("Node {}: has_roles: self.roles: {}".format(self.fqdn, self.roles))
        return bool(self.roles)

    def has_exclusive_role(self, role):
        _log_debug("Node {}: has_exclusive_role: self.roles: {}"
                   .format(self.fqdn, self.roles))
        if role not in KNOWN_ROLES:
            raise RoleNotKnown(role)
        return self.roles == [role]

    def add_repo(self, repo):
        if self.repo_priority:
            if repo.priority is None:
                repo.priority = self._repo_lowest_prio - len(self.repos)
        else:
            repo.priority = None
        self.repos.append(repo)


class NodeManager:
    def __init__(self, nodes):
        self.nodes = nodes

    def get_by_role(self, role):
        return [n for n in self.nodes if n.has_role(role)]

    def get_one_by_role(self, role):
        node_list = self.get_by_role(role)
        if node_list:
            return node_list[0]
        return None

    def get_by_name(self, name):
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def count_by_role(self, role):
        return len(self.get_by_role(role))


def _vet_dep_id(dep_id):
    # from hostname(7) - Linux manual page
    #
    # Each element of the hostname must be from 1 to 63 characters long and the
    # entire hostname, including the dots, can be at most 253 characters long.
    # Valid characters for hostnames are ASCII(7) letters from a to z, the digits
    # from 0 to 9, and the hyphen (-).
    #
    # The dep_id can be interpreted as an "element of the hostname"...
    length = len(dep_id)
    if length < 1 or length > 63:
        raise DepIDWrongLength(length)
    valid_host_regex = r'^[a-z0-9\-]+$'
    if re.search(valid_host_regex, dep_id):
        pass
    else:
        raise DepIDIllegalChars(dep_id)
    return dep_id


class Deployment():
    def __init__(self, dep_id, settings, existing=False):
        if existing:
            self.dep_id = dep_id
        else:
            self.dep_id = _vet_dep_id(dep_id)
        self.settings = settings
        self.existing = existing  # True: we are loading, False: we are creating
        self.nodes = {}
        self.node_counts = {}
        self.nodes_with_role = {}
        for role in KNOWN_ROLES:
            self.node_counts[role] = 0
            self.nodes_with_role[role] = []
        _log_debug("Deployment ctor: node_counts: {}".format(self.node_counts))
        self.master = None
        self.suma = None
        self.box = Box(settings)

        if self.settings.roles:
            pass
        else:
            self.settings.override('roles',
                                   self.settings.version_default_roles[self.settings.version]
                                   )

        if not self.settings.os:
            self.settings.os = VERSION_PREFERRED_OS[self.settings.version]

        if not self.settings.deployment_tool \
                and self.settings.version not in ['caasp4', 'makecheck']:
            self.settings.deployment_tool = VERSION_PREFERRED_DEPLOYMENT_TOOL[self.settings.version]

        if self.settings.deployment_tool == 'cephadm':
            if not self.settings.image_path:
                self.settings.image_path = self.settings.image_paths[self.settings.version]

        if not self.settings.libvirt_networks:
            self._generate_static_networks()

        if self.settings.version == 'makecheck':
            self.settings.override('single_node', True)
            self.settings.override('roles', VERSION_DEFAULT_ROLES['makecheck'])
            if not self.settings.explicit_num_disks:
                self.settings.override('num_disks', 0)
                self.settings.override('explicit_num_disks', True)
            if not self.settings.explicit_ram:
                self.settings.override('ram', GlobalSettings.MAKECHECK_DEFAULT_RAM)
                self.settings.override('explicit_ram', True)

        self._generate_nodes()

    @property
    def _dep_dir(self):
        return os.path.join(GlobalSettings.A_WORKING_DIR, self.dep_id)

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

    def _generate_static_networks(self):
        if self._needs_cluster_network() and self.settings.public_network \
                and self.settings.cluster_network:
            return
        if not self._needs_cluster_network() and self.settings.public_network:
            return

        deps = self.list()
        existing_networks = [dep.settings.public_network for dep in deps
                             if dep.settings.public_network]

        public_network = self.settings.public_network
        while True:
            if not public_network or public_network in existing_networks:
                public_network = "10.20.{}.".format(random.randint(2, 200))
            else:
                break
        self.settings.public_network = public_network

        if self._needs_cluster_network():
            existing_networks = [dep.settings.cluster_network for dep in deps
                                 if dep.settings.cluster_network]

            cluster_network = self.settings.cluster_network
            while True:
                if not cluster_network or cluster_network in existing_networks:
                    cluster_network = "10.21.{}.".format(random.randint(2, 200))
                else:
                    break
            self.settings.cluster_network = cluster_network

    def _generate_nodes(self):
        node_id = 0
        worker_id = 0
        loadbl_id = 0
        nfs_id = 0
        _log_debug("_generate_nodes: about to process cluster roles: {}"
                   .format(self.settings.roles))
        for node_roles in self.settings.roles:  # loop once for every node in cluster
            for role in node_roles:
                if role not in KNOWN_ROLES:
                    raise RoleNotKnown(role)
            for role_type in KNOWN_ROLES:
                if role_type in node_roles:
                    self.node_counts[role_type] += 1

        if self.settings.version in ['ses5', 'ses6', 'nautilus', 'ses7', 'octopus', 'pacific']:
            if self.node_counts['master'] == 0:
                self.settings.roles[0].append('master')
                self.node_counts['master'] = 1
        if self.settings.version in ['ses7', 'octopus', 'pacific']:
            if self.node_counts['bootstrap'] == 0:
                for node_roles in self.settings.roles:
                    if 'mon' in node_roles and 'mgr' in node_roles:
                        node_roles.append('bootstrap')
                        self.node_counts['bootstrap'] = 1
                        break

        storage_nodes = self.node_counts["storage"]
        if not self.settings.explicit_num_disks:
            if storage_nodes:
                if storage_nodes == 1:
                    self.settings.override('num_disks', 4)
                elif storage_nodes == 2:
                    self.settings.override('num_disks', 3)
                else:
                    # go with the default
                    pass
        logger.debug("_generate_nodes: storage_nodes == %s", str(storage_nodes))

        for node_roles in self.settings.roles:  # loop once for every node in cluster
            if self.settings.version == 'caasp4':
                if 'master' in node_roles:
                    node_id += 1
                    name = 'master'
                    fqdn = 'master.{}'.format(self.settings.domain.format(self.dep_id))
                elif 'worker' in node_roles:
                    worker_id += 1
                    node_id += 1
                    name = 'worker{}'.format(worker_id)
                    fqdn = 'worker{}.{}'.format(worker_id,
                                                self.settings.domain.format(self.dep_id))
                elif 'loadbalancer' in node_roles:
                    loadbl_id += 1
                    node_id += 1
                    name = 'loadbl{}'.format(loadbl_id)
                    fqdn = 'loadbl{}.{}'.format(loadbl_id,
                                                self.settings.domain.format(self.dep_id))
                elif 'nfs' in node_roles and self.settings.version == 'caasp4':
                    nfs_id += 1
                    node_id += 1
                    name = 'nfs{}'.format(nfs_id)
                    fqdn = 'nfs{}.{}'.format(nfs_id,
                                             self.settings.domain.format(self.dep_id))
                else:
                    node_id += 1
                    name = 'node{}'.format(node_id)
                    fqdn = 'node{}.{}'.format(node_id,
                                              self.settings.domain.format(self.dep_id))
            else:
                admin_node_processed = False
                if self.existing and 'admin' in node_roles and not admin_node_processed:
                    admin_node_processed = True  # only do this once, for backwards compatibility
                    name = 'admin'
                    fqdn = 'admin.{}'.format(self.settings.domain.format(self.dep_id))
                elif 'master' in node_roles or 'suma' in node_roles or 'makecheck' in node_roles:
                    name = 'master'
                    fqdn = 'master.{}'.format(self.settings.domain.format(self.dep_id))
                else:
                    node_id += 1
                    name = 'node{}'.format(node_id)
                    fqdn = 'node{}.{}'.format(node_id,
                                              self.settings.domain.format(self.dep_id))

            networks = ''
            public_address = None
            if self.settings.libvirt_networks:
                for network in self.settings.libvirt_networks.split(','):
                    networks += (
                        'node.vm.network :private_network,'
                        ':forward_mode => "route", :libvirt__network_name'
                        '=> "{}"\n').format(network)
            else:
                if 'master' in node_roles or 'suma' in node_roles:
                    public_address = '{}{}'.format(self.settings.public_network, 200)
                    networks = ('node.vm.network :private_network, autostart: true, ip:'
                                '"{}"').format(public_address)
                else:
                    public_address = '{}{}'.format(self.settings.public_network, 200 + node_id)
                    networks = ('node.vm.network :private_network, autostart: true, ip:'
                                '"{}"').format(public_address)

            node = Node(name,
                        fqdn,
                        node_roles,
                        networks,
                        public_address=public_address,
                        ram=self.settings.ram * 2**10,
                        cpus=self.settings.cpus,
                        repo_priority=self.settings.repo_priority)

            for role in node_roles:
                self.nodes_with_role[role].append(name)

            if 'master' in node_roles:
                self.master = node

            if self.settings.version == 'caasp4':
                if 'master' in node_roles or 'worker' in node_roles:
                    if node.cpus < 2:
                        node.cpus = 2
                    if self.settings.ram < 2:
                        node.ram = 2 * 2**10
                if 'worker' in node_roles:
                    for _ in range(self.settings.num_disks):
                        node.storage_disks.append(Disk(self.settings.disk_size))
            else:
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

    def _generate_vagrantfile(self):
        vagrant_box = self.settings.os

        try:
            version = self.settings.version
            os_setting = self.settings.os
            version_repos = self.settings.version_os_repo_mapping[version][os_setting]
        except KeyError:
            raise VersionOSNotSupported(self.settings.version, self.settings.os)

        # version_repos might contain URLs with a "magic priority prefix" -- see
        # https://github.com/SUSE/sesdev/issues/162
        version_repos_prio = []
        for repo in version_repos:
            version_repos_dict = {}
            prio_match = re.match(r'^(\d.+)!(http.*)', repo)
            if prio_match:
                version_repos_dict = {
                    "url": prio_match[2],
                    "priority": prio_match[1],
                }
            else:
                version_repos_dict = {
                    "url": repo,
                    "priority": 0,
                }
            version_repos_prio.append(version_repos_dict)
        _log_debug("generate_vagrantfile: version_repos_prio: {}"
                   .format(version_repos_prio))

        if self.settings.os in self.settings.os_repos:
            os_base_repos = list(self.settings.os_repos[self.settings.os].items())
        else:
            os_base_repos = []

        # detect whether we need to fetch github PRs
        ceph_salt_fetch_github_pr_heads = False
        ceph_salt_fetch_github_pr_merges = False
        ceph_salt_git_branch = self.settings.ceph_salt_git_branch
        if ceph_salt_git_branch and ceph_salt_git_branch.startswith('origin/pr/'):
            _log_info("Detected special ceph-salt GitHub PR (HEAD) branch {}"
                      .format(ceph_salt_git_branch)
                      )
            ceph_salt_fetch_github_pr_heads = True
        elif ceph_salt_git_branch and ceph_salt_git_branch.startswith('origin/pr-merged/'):
            _log_info("Detected special ceph-salt GitHub PR (MERGE) branch {}"
                      .format(ceph_salt_git_branch)
                      )
            ceph_salt_fetch_github_pr_merges = True

        context = {
            'ssh_key_name': GlobalSettings.SSH_KEY_NAME,
            'sesdev_path_to_qa': GlobalSettings.PATH_TO_QA,
            'dep_id': self.dep_id,
            'os': self.settings.os,
            'vm_engine': self.settings.vm_engine,
            'libvirt_host': self.settings.libvirt_host,
            'libvirt_user': self.settings.libvirt_user,
            'libvirt_use_ssh': 'true' if self.settings.libvirt_use_ssh else 'false',
            'libvirt_private_key_file': self.settings.libvirt_private_key_file,
            'libvirt_storage_pool': self.settings.libvirt_storage_pool,
            'vagrant_box': vagrant_box,
            'nodes': list(self.nodes.values()),
            'master': self.master,
            'suma': self.suma,
            'domain': self.settings.domain.format(self.dep_id),
            'deepsea_git_repo': self.settings.deepsea_git_repo,
            'deepsea_git_branch': self.settings.deepsea_git_branch,
            'version': self.settings.version,
            'deploy_salt': bool(self.settings.version != 'makecheck' and
                                self.settings.version != 'caasp4' and
                                not self.suma),
            'stop_before_stage': self.settings.stop_before_stage,
            'deployment_tool': self.settings.deployment_tool,
            'version_repos_prio': version_repos_prio,
            'os_base_repos': os_base_repos,
            'repo_priority': self.settings.repo_priority,
            'qa_test': self.settings.qa_test,
            'nfs_nodes': self.node_counts["nfs"],
            'nfs_node_list': ','.join(self.nodes_with_role["nfs"]),
            'igw_nodes': self.node_counts["igw"],
            'igw_node_list': ','.join(self.nodes_with_role["igw"]),
            'mds_nodes': self.node_counts["mds"],
            'mds_node_list': ','.join(self.nodes_with_role["mds"]),
            'mgr_nodes': self.node_counts["mgr"],
            'mgr_node_list': ','.join(self.nodes_with_role["mgr"]),
            'mon_nodes': self.node_counts["mon"],
            'mon_node_list': ','.join(self.nodes_with_role["mon"]),
            'rgw_nodes': self.node_counts["rgw"],
            'rgw_node_list': ','.join(self.nodes_with_role["rgw"]),
            'storage_nodes': self.node_counts["storage"],
            'storage_node_list': ','.join(self.nodes_with_role["storage"]),
            'deepsea_need_stage_4': bool(self.node_counts["nfs"] or self.node_counts["igw"]
                                         or self.node_counts["mds"] or self.node_counts["rgw"]
                                         or self.node_counts["openattic"]),
            'total_osds': self.settings.num_disks * self.node_counts["storage"],
            'encrypted_osds': self.settings.encrypted_osds,
            'scc_username': self.settings.scc_username,
            'scc_password': self.settings.scc_password,
            'ceph_salt_git_repo': self.settings.ceph_salt_git_repo,
            'ceph_salt_git_branch': self.settings.ceph_salt_git_branch,
            'ceph_salt_fetch_github_pr_heads': ceph_salt_fetch_github_pr_heads,
            'ceph_salt_fetch_github_pr_merges': ceph_salt_fetch_github_pr_merges,
            'stop_before_ceph_salt_config': self.settings.stop_before_ceph_salt_config,
            'stop_before_ceph_salt_apply': self.settings.stop_before_ceph_salt_apply,
            'stop_before_ceph_orch_apply': self.settings.stop_before_ceph_orch_apply,
            'image_path': self.settings.image_path,
            'use_salt': self.settings.use_salt,
            'node_manager': NodeManager(list(self.nodes.values())),
            'caasp_deploy_ses': self.settings.caasp_deploy_ses,
            'synced_folders': self.settings.synced_folder,
            'makecheck_ceph_repo': self.settings.makecheck_ceph_repo,
            'makecheck_ceph_branch': self.settings.makecheck_ceph_branch,
            'makecheck_username': self.settings.makecheck_username,
            'makecheck_stop_before_git_clone': self.settings.makecheck_stop_before_git_clone,
            'makecheck_stop_before_install_deps': self.settings.makecheck_stop_before_install_deps,
            'makecheck_stop_before_run_make_check':
                self.settings.makecheck_stop_before_run_make_check,
        }

        scripts = {}

        for node in self.nodes.values():
            context_cpy = dict(context)
            context_cpy['node'] = node
            template = JINJA_ENV.get_template('provision.sh.j2')
            scripts['provision_{}.sh'.format(node.name)] = template.render(**context_cpy)

        template = JINJA_ENV.get_template('Vagrantfile.j2')
        scripts['Vagrantfile'] = template.render(**context)
        return scripts

    def save(self):
        scripts = self._generate_vagrantfile()
        key = RSA.generate(2048)
        private_key = key.exportKey('PEM')
        public_key = key.publickey().exportKey('OpenSSH')

        os.makedirs(self._dep_dir, exist_ok=False)
        metadata_file = os.path.join(self._dep_dir, METADATA_FILENAME)
        with open(metadata_file, 'w') as file:
            json.dump({
                'id': self.dep_id,
                'settings': self.settings
            }, file, cls=SettingsEncoder)

        for filename, script in scripts.items():
            full_path = os.path.join(self._dep_dir, filename)
            with open(full_path, 'w') as file:
                file.write(script)

        # generate ssh key pair
        keys_dir = os.path.join(self._dep_dir, 'keys')
        os.makedirs(keys_dir)

        with open(os.path.join(keys_dir, GlobalSettings.SSH_KEY_NAME), 'w') as file:
            file.write(private_key.decode('utf-8'))
        os.chmod(os.path.join(keys_dir, GlobalSettings.SSH_KEY_NAME), 0o600)

        with open(os.path.join(keys_dir, str(GlobalSettings.SSH_KEY_NAME + '.pub')), 'w') as file:
            file.write(str(public_key.decode('utf-8') + " sesdev\n"))
        os.chmod(os.path.join(keys_dir, str(GlobalSettings.SSH_KEY_NAME + '.pub')), 0o600)

        # bin dir with helper scripts
        bin_dir = os.path.join(self._dep_dir, 'bin')
        os.makedirs(bin_dir)

    def _get_vagrant_box(self, log_handler):
        if self.settings.vagrant_box:
            using_custom_box = True
            vagrant_box = self.settings.vagrant_box
        else:
            using_custom_box = False
            vagrant_box = self.settings.os

        _log_info("Checking if vagrant box is already here: {}"
                  .format(vagrant_box))
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

            image_to_remove = self.box.get_image_by_box(self.settings.os)
            if image_to_remove:
                # remove image in libvirt to guarantee that, when "vagrant up"
                # runs, the new box will be uploaded to libvirt
                self.box.remove_image(image_to_remove)

            tools.run_async(["vagrant", "box", "add", "--provider", "libvirt", "--name",
                             self.settings.os, OS_BOX_MAPPING[self.settings.os]], log_handler)

    def _vagrant_up(self, node, log_handler):
        cmd = ["vagrant", "up"]
        if node is not None:
            cmd.append(node)
        if GlobalSettings.VAGRANT_DEBUG:
            cmd.append('--debug')
        tools.run_async(cmd, log_handler, self._dep_dir)

    def destroy(self, log_handler, destroy_networks=False):

        # if we are allowing networks to be destroyed, populate the networks
        # list; we will find all networks now, and we'll destroy them last.
        used_networks = []
        if destroy_networks:
            used_networks = self.box.get_networks_by_deployment(self.dep_id)

        logger.debug("should destroy networks: %s, networks: %s",
                     destroy_networks, used_networks)

        for node in self.nodes.values():
            if node.status == 'not deployed':
                continue
            cmd = ["vagrant", "destroy", node.name, "--force"]
            if GlobalSettings.VAGRANT_DEBUG:
                cmd.append('--debug')
            tools.run_async(cmd, log_handler, self._dep_dir)

        shutil.rmtree(self._dep_dir)
        # clean up any orphaned volumes
        images_to_remove = self.box.get_images_by_deployment(self.dep_id)
        if images_to_remove:
            log_handler("Found orphaned volumes: {}".format(images_to_remove))
            log_handler("Removing them!")
            for image in images_to_remove:
                self.box.remove_image(image)

        for network in used_networks:
            logger.info("Destroy network '%s'", network)
            if not self.box.destroy_network(network):
                logger.warning(
                    "Unable to destroy network '%s' for deployment '%s'",
                    network, self.dep_id)
            else:
                logger.info("Destroyed network '%s' for deployment '%s'",
                            network, self.dep_id)

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
            log_handler("Stopping node {} of deployment {}\n".format(node, self.dep_id))
            self._stop(node)
        else:
            for _node in self.nodes:
                log_handler("Stopping node {} of deployment {}\n".format(_node, self.dep_id))
                self._stop(_node)

    def start(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise NodeDoesNotExist(node)

        if self.settings.vm_engine == 'libvirt':
            self._get_vagrant_box(log_handler)
        self._vagrant_up(node, log_handler)

    def __str__(self):
        return self.dep_id

    def load_status(self):
        if not os.path.exists(os.path.join(self._dep_dir, '.vagrant')):
            for node in self.nodes.values():
                node.status = "not deployed"
            return

        out = tools.run_sync(["vagrant", "status"], cwd=self._dep_dir)
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
        result = "{} Deployment VMs:\n".format(len(self.nodes))
        for k, v in self.nodes.items():
            result += "  -- {}:\n".format(k)
            if v.status:
                result += "     - status:           {}\n".format(v.status)
            result += "     - OS:               {}\n".format(self.settings.os)
            result += "     - ses_version:      {}\n".format(self.settings.version)
            if k == 'master':
                result += "     - deployment_tool:  {}\n".format(self.settings.deployment_tool)
            result += "     - roles:            {}\n".format(v.roles)
            if self.settings.version in ["octopus", "ses7", "pacific"]:
                if 'admin' not in v.roles and v.roles != [] and v.roles != ['client']:
                    result += (
                        "                         (CAVEAT: the 'admin' role is assumed"
                        " even though not explicitly given!)\n"
                        )
            if self.settings.vagrant_box:
                result += "     - vagrant_box       {}\n".format(self.settings.vagrant_box)
            result += "     - fqdn:             {}\n".format(v.fqdn)
            if v.public_address:
                result += "     - public_address:   {}\n".format(v.public_address)
            if v.cluster_address:
                result += "     - cluster_address:  {}\n".format(v.cluster_address)
            result += "     - cpus:             {}\n".format(v.cpus)
            result += "     - ram:              {}G\n".format(int(v.ram / (2 ** 10)))
            if v.storage_disks:
                result += "     - storage_disks:    {}\n".format(len(v.storage_disks))
                result += ("                         "
                           "(device names will be assigned by vagrant-libvirt)\n")
                result += "     - encrypted OSDs:   {}\n".format(self.settings.encrypted_osds)
            result += "     - repo_priority:    {}\n".format(self.settings.repo_priority)
            result += "     - qa_test:          {}\n".format(self.settings.qa_test)
            if self.settings.version in ['octopus', 'ses7', 'pacific']:
                result += "     - image_path:       {}\n".format(self.settings.image_path)
            for synced_folder in self.settings.synced_folder:
                result += "     - synced_folder:    {}\n".format(' -> '.join(synced_folder))
            if v.repos:
                result += "     - custom_repos:\n"
                for repo in v.repos:
                    result += "       - {}\n".format(repo.url)
            result += "\n"
        return result

    def vet_configuration(self):
        # "admin" role exists for backwards compatibility with existing
        # deployments only, and should not be used for new deployments
        if self.node_counts['admin'] != 0:
            raise ExplicitAdminRoleNotAllowed()
        # all deployment versions except "makecheck" require one, and only one, master role
        if self.settings.version == 'makecheck':
            if len(self.nodes) == 1 and self.node_counts['makecheck'] == 1:
                pass
            else:
                raise BadMakeCheckRolesNodes()
        else:
            if self.node_counts['master'] != 1:
                raise UniqueRoleViolation('master', self.node_counts['master'])
        # octopus and beyond require one, and only one, bootstrap role
        if self.settings.version in ['ses7', 'octopus']:
            if self.node_counts['bootstrap'] != 1:
                raise UniqueRoleViolation('bootstrap', self.node_counts['bootstrap'])
        # there must not be more than one suma role:
        if self.node_counts['suma'] > 1:
            raise UniqueRoleViolation('suma', self.node_counts['suma'])
        # openattic role only in ses5
        if self.node_counts['openattic'] > 0 and self.settings.version != 'ses5':
            raise RoleNotSupported('openattic', self.settings.version)
        # ses5 DeepSea does not recognize prometheus and grafana roles
        if self.settings.version == 'ses5':
            if self.node_counts['prometheus'] > 0 or self.node_counts['grafana'] > 0:
                raise NoPrometheusGrafanaInSES5()
        # suma role only in octopus and not together with master
        if self.suma:
            if self.settings.version not in 'octopus':
                raise RoleNotSupported('suma', self.settings.version)
            if self.suma == self.master:
                raise ExclusiveRoles('master', 'suma')
        # worker and loadbalancer only in caasp4
        if self.settings.version not in 'caasp4':
            if self.node_counts['worker'] > 0:
                raise RoleNotSupported('worker', self.settings.version)
            if self.node_counts['loadbalancer'] > 0:
                raise RoleNotSupported('loadbalancer', self.settings.version)
        # no node may have more than one of any role
        for node in self.settings.roles:
            for role in KNOWN_ROLES:
                if node.count(role) > 1:
                    raise DuplicateRolesNotSupported(role)

    def _vagrant_ssh_config(self, name):
        if name not in self.nodes:
            raise NodeDoesNotExist(name)

        out = tools.run_sync(["vagrant", "ssh-config", name], cwd=self._dep_dir)

        address = None
        proxycmd = None
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('HostName'):
                address = line[len('HostName')+1:]
            elif line.startswith('ProxyCommand'):
                proxycmd = line[len('ProxyCommand')+1:]

        if address is None:
            raise VagrantSshConfigNoHostName(name)

        dep_private_key = os.path.join(self._dep_dir, str("keys/" + GlobalSettings.SSH_KEY_NAME))

        return (address, proxycmd, dep_private_key)

    @staticmethod
    def _parse_source_destination(source, destination):
        host_is_source = False
        host_is_destination = False
        name = None
        source_path = None
        destination_path = None

        # populate host_is_source and host_is_destination
        if ':' in source:
            host_is_source = False
            host_is_destination = True
        if ':' in destination:
            host_is_source = True
            host_is_destination = False
        if host_is_source and host_is_destination:
            raise ScpInvalidSourceOrDestination
        if host_is_source or host_is_destination:
            pass
        else:
            raise ScpInvalidSourceOrDestination

        # populate name, source_path, and destination_path
        if host_is_source:
            source_path = source
            (name, destination_path) = destination.split(':')
        elif host_is_destination:
            (name, source_path) = source.split(':')
            destination_path = destination

        return (host_is_source, host_is_destination, name, source_path, destination_path)

    @staticmethod
    def __boilerplate_ssh_options(string=False):
        retval = None
        if string:
            retval = (
                " -o 'IdentitiesOnly yes'"
                " -o 'StrictHostKeyChecking no'"
                " -o 'UserKnownHostsFile /dev/null'"
                " -o 'PasswordAuthentication no'"
                )
        else:
            retval = [
                "-o", "IdentitiesOnly yes",
                "-o", "StrictHostKeyChecking no",
                "-o", "UserKnownHostsFile /dev/null",
                "-o", "PasswordAuthentication no",
                ]
        return retval

    def _ssh_cmd(self, name, command=None):
        (address, proxycmd, dep_private_key) = self._vagrant_ssh_config(name)
        _cmd = [
            "ssh",
            "root@{}".format(address),
            "-i", dep_private_key
            ]
        _cmd.extend(self.__boilerplate_ssh_options())
        if proxycmd is not None:
            _cmd.extend(["-o", "ProxyCommand={}".format(proxycmd)])
        if command:
            _cmd.extend(command)
        return _cmd

    def ssh(self, name, command):
        return tools.run_interactive(self._ssh_cmd(name, command))

    def _scp_cmd(self, source, destination, recurse=False):
        (host_is_source,
         host_is_destination,
         name,
         source_path,
         destination_path) = self._parse_source_destination(source, destination)

        # build up scp command
        (address, proxycmd, dep_private_key) = self._vagrant_ssh_config(name)
        _cmd = ['scp']
        if recurse:
            _cmd.extend(['-r'])
        _cmd.extend(["-i", dep_private_key])
        _cmd.extend(self.__boilerplate_ssh_options())
        if proxycmd is not None:
            _cmd.extend(["-o", "ProxyCommand={}".format(proxycmd)])
        if host_is_source:
            _cmd.extend([source_path, 'root@{}:{}'.format(address, destination_path)])
        elif host_is_destination:
            _cmd.extend(['root@{}:{}'.format(address, source_path), destination_path])

        return _cmd

    def scp(self, source, destination, recurse=False):
        tools.run_interactive(self._scp_cmd(source, destination, recurse=recurse))

    def _rsync_cmd(self, source, destination, excludes=None, recurse=False):
        (host_is_source,
         host_is_destination,
         name,
         source_path,
         destination_path) = self._parse_source_destination(source, destination)

        # build up rsync command
        (address, proxycmd, dep_private_key) = self._vagrant_ssh_config(name)
        _cmd = ['rsync']
        if recurse:
            _cmd.extend(['-r'])
        if excludes:
            for exclude in excludes:
                _cmd.extend(['--exclude={}'.format(exclude)])
        proxycmd_opt = ''
        if proxycmd is not None:
            proxycmd_opt = " -o 'ProxyCommand={}'".format(proxycmd)
        _cmd.extend(["-e", "ssh -i {}{}{}".format(
            dep_private_key,
            self.__boilerplate_ssh_options(string=True),
            proxycmd_opt
            )])
        if host_is_source:
            _cmd.extend([source_path, 'root@{}:{}'.format(address, destination_path)])
        elif host_is_destination:
            _cmd.extend(['root@{}:{}'.format(address, source_path), destination_path])

        return _cmd

    def rsync(self, source, destination, excludes=None, recurse=False):
        tools.run_interactive(self._rsync_cmd(source, destination, excludes, recurse=recurse))

    def supportconfig(self, log_handler, name):
        if self.settings.os.startswith("sle"):
            log_msg = ("The OS ->{}<- is SLE, where supportconfig is available"
                       .format(self.settings.os))
            logger.debug(log_msg)
        else:
            raise SupportconfigOnlyOnSLE()
        log_handler("=> Running supportconfig on deployment ID: {} (OS: {})\n".format(
            self.dep_id,
            self.settings.os
            ))
        self.ssh(name, ('supportconfig',))
        log_handler("=> Grabbing the resulting tarball from the cluster node\n")
        scc_exists = self.ssh(name, ('ls', '/var/log/scc*'))
        nts_exists = self.ssh(name, ('ls', 'var/log/nts*'))
        glob_to_get = None
        if scc_exists == 0:
            log_handler("Found /var/log/scc* (supportconfig) files on {}\n".format(name))
            glob_to_get = 'scc*'
        elif nts_exists == 0:
            log_handler("Found /var/log/nts* (supportconfig) files on {}\n".format(name))
            glob_to_get = 'nts*'
        else:
            raise NoSupportConfigTarballFound(name)
        self.scp('{n}:/var/log/{g}'.format(n=name, g=glob_to_get), '.')
        log_handler("=> Deleting the tarball from the cluster node\n")
        self.ssh(name, ('rm', '/var/log/{}'.format(glob_to_get)))

    def qa_test(self, log_handler):
        tools.run_async(
            ["vagrant", "provision", "--provision-with", "qa-test"],
            log_handler,
            self._dep_dir
            )

    def _find_service_node(self, service):
        if service in ['prometheus', 'grafana'] and self.settings.version == 'ses5':
            return 'master'
        nodes = [name for name, node in self.nodes.items() if service in node.roles]
        return nodes[0] if nodes else None

    def start_port_forwarding(self, service=None, node=None, remote_port=None, local_port=None,
                              local_address=None):
        if local_address is None:
            local_address = 'localhost'

        if service is not None:
            if service not in ['dashboard', 'grafana', 'openattic', 'suma', 'prometheus',
                               'alertmanager']:
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
                if self.settings.version == 'ses5':
                    raise ServiceNotFound(service)
                remote_port = 8443
                local_port = 8443
                service_url = 'https://{}:{}'.format(local_address, local_port)
                ssh_cmd = self._ssh_cmd('master')
                ssh_cmd += ["ceph", "mgr", "services"]
                _log_debug("About to run: {}".format(ssh_cmd))
                try:
                    raw_json = tools.run_sync(ssh_cmd)
                    raw_json = raw_json.strip()
                    _log_debug("Got output: {}".format(raw_json))
                    decoded_json = json.loads(raw_json)
                    _log_debug("Decoded json: {}".format(decoded_json))
                    dashboard_url = decoded_json['dashboard']
                    _log_debug("Dashboard URL: {}".format(dashboard_url))
                    node = re.match(r"https://([^.]*).*", dashboard_url).group(1)
                    _log_debug("Extracted node: {}".format(node))
                except (CmdException, AttributeError, KeyError):
                    node = 'null'
                if node == 'null':
                    raise ServiceNotFound(service)
                print("dashboard is running on node '{}'".format(node))
            elif service == 'suma':
                node = 'master'
                remote_port = 443
                local_port = 8443
                service_url = 'https://{}:{}'.format(local_address, local_port)
            elif service == 'prometheus':
                node = self._find_service_node(service)
                remote_port = 9090
                local_port = 9090
                service_url = 'http://{}:{}'.format(local_address, local_port)
            elif service == 'alertmanager':
                node = self._find_service_node(service)
                remote_port = 9093
                local_port = 9093
                service_url = 'http://{}:{}'.format(local_address, local_port)
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
        _log_debug("About to run: {}".format(ssh_cmd))
        print("You can now access the service in: {}".format(service_url))
        tools.run_sync(ssh_cmd)

    def replace_ceph_salt(self, local=None):
        root = '/root'
        ceph_salt_src = '{}/ceph-salt'.format(root)
        master_node = 'master'

        print("Fetching ceph-salt...")
        if local:
            self.rsync(local,
                       '{}:{}'.format(master_node, root),
                       excludes=['.git', '.tox', '.idea', 'venv'],
                       recurse=True)

        print("Installing ceph-salt...")
        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("cp -r {}/ceph-salt-formula/salt/* /srv/salt/".format(ceph_salt_src))
        tools.run_sync(ssh_cmd)

        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("zypper --non-interactive refresh")
        tools.run_sync(ssh_cmd)

        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("zypper --non-interactive install python3-pip")
        tools.run_sync(ssh_cmd)

        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("zypper --non-interactive remove ceph-salt ceph-salt-formula || true")
        tools.run_sync(ssh_cmd)

        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("pip install --prefix /usr {}".format(ceph_salt_src))
        tools.run_sync(ssh_cmd)

        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("salt '*' saltutil.sync_all")
        tools.run_sync(ssh_cmd)

    def replace_mgr_modules(self, local=None, pr=None, branch=None, repo=None, langs=None):
        if self.settings.version in ['nautilus', 'ses6', 'octopus', 'ses7', 'pacific']:
            pass  # replace-mgr-modules is expected to work with these
        else:
            raise SubcommandNotSupportedInVersion('replace-mgr-modules', self.settings.version)

        if local:
            print("Using local repository '{}' ...".format(local))
        elif pr:
            print("Fetching PR '{}' from '{}'...".format(pr, repo))
        elif branch:
            print("Fetching branch '{}' from '{}'...".format(branch, repo))

        master_node = 'master'
        mgr_nodes = []

        for _node in self.nodes.values():
            if _node.has_role('mgr'):
                mgr_nodes.append(_node.name)

        print("Disabling modules...")
        ssh_cmd = self._ssh_cmd(mgr_nodes[0])
        ssh_cmd.append("ceph mgr module ls | jq -r '.enabled_modules | .[]'")
        modules = tools.run_sync(ssh_cmd)
        if modules:
            modules = modules.strip().split('\n')
        print("{}".format(modules))
        for module in modules:
            ssh_cmd = self._ssh_cmd(mgr_nodes[0])
            ssh_cmd.append("ceph mgr module disable {}".format(module))
            tools.run_sync(ssh_cmd)

        print("Fetching...")
        if local:
            local_path = "{}/src/pybind/mgr".format(local)
            master_path = "/root/local/ceph/src/pybind"

            ssh_cmd = self._ssh_cmd(master_node)
            ssh_cmd.append("rm -rf {0} && mkdir -p {0}".format(master_path))
            tools.run_sync(ssh_cmd)

            self.rsync(local_path,
                       '{}:{}'.format(master_node, master_path),
                       excludes=['.git', '.tox', '.idea', 'venv', 'build',
                                 'node_modules', 'cypress', 'frontend/src'],
                       recurse=True)
        else:
            master_path = "/root/remote/ceph/src/pybind"

            if pr:
                remote_branch = 'pull/{}/head'.format(pr)
            else:
                remote_branch = branch

            local_branch = '{}/{}'.format(repo, remote_branch)

            if "//" not in repo:
                repo = "https://github.com/{0}/ceph.git".format(repo)

            ssh_cmd = self._ssh_cmd(master_node)
            ssh_cmd.append(
                "cd ~/ && \
                [ -d 'remote' ] || mkdir remote && \
                cd remote && \
                [ -d 'ceph' ] || git clone --depth 1 {0} && \
                cd ceph && \
                git checkout master && \
                git fetch --depth 1 {0} {1}:{2} -f && \
                git checkout {2}"
                .format(repo, remote_branch, local_branch))
            tools.run_sync(ssh_cmd)

            print("Building...")
            npm_build = "build:localize"
            node_version = "12.18.0"
            if self.settings.version in ['nautilus', 'ses6', 'octopus', 'ses7']:
                npm_build = "build"
                node_version = "10.18.1"

            ssh_cmd = self._ssh_cmd(master_node)
            ssh_cmd.append(
                "cd ~/ && \
                zypper -n in python2-pip python3-pip && \
                pip install nodeenv && \
                nodeenv env --node={} --force && \
                . ~/env/bin/activate && \
                cd {}/mgr/dashboard/frontend && \
                export DASHBOARD_FRONTEND_LANGS='{}' && \
                export NG_CLI_ANALYTICS=false && \
                npm ci --unsafe-perm && \
                npm run {} && \
                rm -rf node_modules"
                .format(node_version, master_path, langs, npm_build))
            tools.run_sync(ssh_cmd)

        for node in mgr_nodes:
            if self.settings.version in ['nautilus', 'ses6']:
                print("Copying to node {}".format(node))
                self.rsync(
                    '{}:{}/mgr'.format(master_node, master_path),
                    "{}:/usr/share/ceph/".format(node),
                    excludes=['.git', '.tox', '.idea', 'venv', 'build',
                              'node_modules', 'cypress'],
                    recurse=True)

                ssh_cmd = self._ssh_cmd(master_node)
                ssh_cmd.append("scp -r {}/mgr/ {}:/usr/share/ceph/"
                               .format(master_path, node))
                tools.run_sync(ssh_cmd)
            else:
                ssh_cmd = self._ssh_cmd(node)
                ssh_cmd.append('podman ps --format "{}" -f name=mgr.{}'.format("{{.ID}}", node))
                containers = tools.run_sync(ssh_cmd)
                containers = containers.strip().split('\n')

                print("Copying to node {}".format(node))
                ssh_cmd = self._ssh_cmd(node)
                ssh_cmd.append("rm -rf ~/mgr")
                tools.run_sync(ssh_cmd)

                ssh_cmd = self._ssh_cmd(master_node)
                ssh_cmd.append("scp -r {}/mgr/ {}:~/".format(master_path, node))
                tools.run_sync(ssh_cmd)

                for container in containers:
                    print("Copying to the container {}".format(container))
                    ssh_cmd = self._ssh_cmd(node)
                    ssh_cmd.append("podman exec {}".format(container))
                    ssh_cmd.append("rm -rf /usr/share/ceph/mgr/dashboard/frontend/dist/")
                    tools.run_sync(ssh_cmd)

                    ssh_cmd = self._ssh_cmd(node)
                    ssh_cmd.append("podman cp ~/mgr {}:/usr/share/ceph/"
                                   .format(container))
                    tools.run_sync(ssh_cmd)

        print("Enabling modules...")
        for module in modules:
            ssh_cmd = self._ssh_cmd(mgr_nodes[0])
            ssh_cmd.append("ceph mgr module enable {}".format(module))
            tools.run_sync(ssh_cmd)

    @classmethod
    def create(cls, dep_id, settings):
        dep_dir = os.path.join(GlobalSettings.A_WORKING_DIR, dep_id)
        if os.path.exists(dep_dir):
            raise DeploymentAlreadyExists(dep_id)

        dep = cls(dep_id, settings)
        logger.info("creating new deployment: %s", dep)
        dep.save()
        return dep

    @classmethod
    def load(cls, dep_id, load_status=True):
        dep_dir = os.path.join(GlobalSettings.A_WORKING_DIR, dep_id)
        if not os.path.exists(dep_dir) or not os.path.isdir(dep_dir):
            logger.debug("%s does not exist or is not a directory", dep_dir)
            raise DeploymentDoesNotExists(dep_id)
        metadata_file = os.path.join(dep_dir, METADATA_FILENAME)
        if not os.path.exists(metadata_file) or not os.path.isfile(metadata_file):
            logger.debug("metadata file %s does not exist or is not a file", metadata_file)
            raise DeploymentDoesNotExists(dep_id)

        with open(metadata_file, 'r') as file:
            metadata = json.load(file)

        dep = cls(metadata['id'], Settings(strict=False, **metadata['settings']), existing=True)
        if load_status:
            dep.load_status()
        return dep

    @classmethod
    def list(cls, load_status=False):
        deps = []
        if not os.path.exists(GlobalSettings.A_WORKING_DIR):
            return deps
        for dep_id in os.listdir(GlobalSettings.A_WORKING_DIR):
            if dep_id.startswith("config.yaml"):
                logger.debug("Skipping %s (obviously not a deployment)", dep_id)
                continue
            try:
                deps.append(Deployment.load(dep_id, load_status))
            except DeploymentDoesNotExists:
                continue
        return deps
