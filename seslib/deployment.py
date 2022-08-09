import inspect
import json
import os
import random
import re
import shutil
import time

try:
    from typing import Iterable, List
except ImportError:
    pass

from Cryptodome.PublicKey import RSA

from . import tools
from .box import Box
from .constant import Constant
from .exceptions import \
                        BadMakeCheckRolesNodes, \
                        CmdException, \
                        DeploymentAlreadyExists, \
                        DeploymentDoesNotExists, \
                        DeploymentIncompatible, \
                        DepIDWrongLength, \
                        DepIDIllegalChars, \
                        DuplicateRolesNotSupported, \
                        ExclusiveRoles, \
                        MultipleRolesPerMachineNotAllowedInCaaSP, \
                        NodeDoesNotExist, \
                        NodeMustBeAdminAsWell, \
                        NoGaneshaRolePostNautilus, \
                        NoPrometheusGrafanaInSES5, \
                        NoSourcePortForPortForwarding, \
                        NoStorageRolesDeepsea, \
                        NoStorageRolesCephadm, \
                        NoSupportConfigTarballFound, \
                        ProductOptionOnlyOnSES, \
                        RebootDidNotSucceed, \
                        RoleNotKnown, \
                        RoleNotSupported, \
                        ScpInvalidSourceOrDestination, \
                        ServiceNotFound, \
                        ServicePortForwardingNotSupported, \
                        SubcommandNotSupportedInVersion, \
                        SupportconfigOnlyOnSLE, \
                        VagrantSshConfigNoHostName, \
                        VersionOSNotSupported, \
                        UniqueRoleViolation, \
                        UnsupportedVMEngine, \
                        UpgradeNotSupported
from .log import Log
from .node import Node, NodeManager
from .settings import Settings, SettingsEncoder
from .zypper import ZypperRepo, ZypperPackage


class Disk():
    def __init__(self, size):
        self.size = size


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


class Deployment():  # use Deployment.create() to create a Deployment object

    def __init__(self, dep_id, settings, existing=False):
        Log.info("Instantiating deployment {}".format(dep_id))
        if existing:
            self.dep_id = dep_id
        else:
            self.dep_id = _vet_dep_id(dep_id)
        self.settings = settings
        self.domain = self.settings.domain.format(self.dep_id)
        self.existing = existing  # True: we are loading, False: we are creating
        self.nodes = {}
        self.node_counts = {}
        self.nodes_with_role = {}
        self.public_network_segment = "{}0/24".format(self.settings.public_network) \
            if self.settings.public_network else None
        self.cluster_network_segment = "{}0/24".format(self.settings.cluster_network) \
            if self.settings.cluster_network else None
        self.roles_of_nodes = {}
        for role in Constant.ROLES_KNOWN:
            self.node_counts[role] = 0
            self.nodes_with_role[role] = []
        Log.debug("Deployment ctor: node_counts: {}".format(self.node_counts))
        self.master = None
        self.suma = None
        self.vagrant_box = None
        self.box = Box(settings)
        self.bootstrap_mon_ip = None
        self.version_devel_repos = None
        self.os_base_repos = None
        self.os_ca_repo = None
        self.internal_media_repo = None
        self.developer_tools_repos = None
        self.os_makecheck_repos = None
        self.os_upgrade_repos = None
        self.upgrade_devel_repos = None
        self.ceph_salt_fetch_github_pr_heads = None
        self.ceph_salt_fetch_github_pr_merges = None
        self.cephadm_bootstrap_node = None
        self.__populate_roles()
        self.__count_roles()
        self.__populate_os()
        self.__populate_deployment_tool()
        self.__populate_container_registry()
        self.__populate_image_paths()
        if not self.settings.libvirt_networks and not existing:
            self.__generate_static_networks()
        if self.settings.version in ['makecheck']:
            self.__set_up_make_check()
        self.__maybe_tweak_roles()
        self.__maybe_adjust_num_disks()
        self.__generate_nodes()
        self.__get_extra_ssh_keys()
        self.node_list = ','.join(self.nodes.keys())

    def __populate_roles(self):
        if self.settings.roles:
            pass
        else:
            self.settings.override('roles',
                                   self.settings.version_default_roles[self.settings.version]
                                   )

    def __count_roles(self):
        for node_roles in self.settings.roles:  # loop once for every node in cluster
            for role in node_roles:
                if role not in Constant.ROLES_KNOWN:
                    raise RoleNotKnown(role)
            for role_type in Constant.ROLES_KNOWN:
                if role_type in node_roles:
                    self.node_counts[role_type] += 1

    def __populate_os(self):
        if not self.settings.os:
            self.settings.os = Constant.VERSION_PREFERRED_OS[self.settings.version]

    def __populate_deployment_tool(self):
        if not self.settings.deployment_tool \
                and self.settings.version not in ['caasp4', 'makecheck']:
            self.settings.deployment_tool = \
                Constant.VERSION_PREFERRED_DEPLOYMENT_TOOL[self.settings.version]

    def __populate_container_registry(self):
        if self.settings.container_registry:
            reg = dict(
                prefix=self.settings.container_registry.get('prefix'),
                location=self.settings.container_registry.get('location'),
                insecure=self.settings.container_registry.get('insecure'),
            )
            self.settings.reg = reg
        else:
            self.settings.reg = None

    def __populate_image_paths(self):
        """
        Set the image paths based on the `devel_repo` setting to either "devel"
        or "product".
        """
        if self.settings.deployment_tool != 'cephadm':
            return

        if self.settings.devel_repo:
            image_paths = self.settings.image_paths_devel[self.settings.version]
        else:
            image_paths = self.settings.image_paths_product[self.settings.version]

        if isinstance(image_paths, str):
            # preserves compatibility to start, stop and destroy older deployments
            self.settings.ceph_image_path = image_paths
            Log.info(
                f'Loaded outdated deployment {self.dep_id}. '
                f'No issues are to be expected because of that.'
            )
        else:
            if self.settings.ceph_image_path == '':
                self.settings.ceph_image_path = image_paths['ceph']  # must be specified
            if self.settings.grafana_image_path == '':
                self.settings.grafana_image_path = image_paths.get('grafana')
            if self.settings.prometheus_image_path == '':
                self.settings.prometheus_image_path = image_paths.get('prometheus')
            if self.settings.node_exporter_image_path == '':
                self.settings.node_exporter_image_path = image_paths.get('node-exporter')
            if self.settings.alertmanager_image_path == '':
                self.settings.alertmanager_image_path = image_paths.get('alertmanager')
            if self.settings.haproxy_image_path == '':
                self.settings.haproxy_image_path = image_paths.get('haproxy')
            if self.settings.keepalived_image_path == '':
                self.settings.keepalived_image_path = image_paths.get('keepalived')
            if self.settings.snmp_gateway_image_path == '':
                self.settings.snmp_gateway_image_path = image_paths.get('snmp-gateway')

    def __get_extra_ssh_keys(self):
        Log.debug('__get_extra_ssh_keys')
        self._extra_ssh_keys = []

        try:
            keylines = tools.run_sync(['ssh-add', '-L']).splitlines()
        except CmdException as _e:
            Log.info('Could not fetch keys from ssh agent: {}'.format(_e.stderr))
            keylines = []

        for line in keylines:
            _, _, _keyid = line.split()
            if _keyid in self.settings.ssh_extra_auth_keys:
                Log.info('found extra key {}'.format(_keyid))
                self._extra_ssh_keys.append({
                    'keyid': _keyid,
                    'keyline': line,
                    })

    def __set_up_make_check(self):
        self.settings.override('single_node', True)
        self.settings.override('roles', Constant.ROLES_DEFAULT_BY_VERSION['makecheck'])
        if not self.settings.explicit_num_disks:
            self.settings.override('num_disks', [0])
            self.settings.override('explicit_num_disks', True)
        if not self.settings.explicit_ram:
            self.settings.override('ram', Constant.MAKECHECK_DEFAULT_RAM)
            self.settings.override('explicit_ram', True)
        if not self.settings.makecheck_ceph_repo:
            self.settings.override(
                'makecheck_ceph_repo',
                Constant.MAKECHECK_DEFAULT_REPO_BRANCH[self.settings.os]['repo']
            )
        if not self.settings.makecheck_ceph_branch:
            self.settings.override(
                'makecheck_ceph_branch',
                Constant.MAKECHECK_DEFAULT_REPO_BRANCH[self.settings.os]['branch']
            )

    def __maybe_tweak_roles(self):
        if self.settings.version in Constant.CORE_VERSIONS:
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

    def __maybe_adjust_num_disks(self):
        single_node = self.settings.single_node or len(self.settings.roles) == 1
        storage_nodes = self.node_counts["storage"]
        if self.settings.version in ['caasp4'] and self.settings.caasp_deploy_ses:
            if single_node:
                storage_nodes = 1
            else:
                storage_nodes = self.node_counts["worker"]
        Log.debug("__maybe_adjust_num_disks: storage_nodes == {}".format(storage_nodes))
        if not self.settings.explicit_num_disks and storage_nodes:
            new_num_disks = None
            if storage_nodes == 1:
                new_num_disks = 4
            elif storage_nodes == 2:
                new_num_disks = 3
            else:
                new_num_disks = self.settings.num_disks  # go with the default
            if self.settings.ssd and new_num_disks:
                new_num_disks += 1
            if new_num_disks:
                self.settings.override('num_disks', [new_num_disks])

    @property
    def _dep_dir(self):
        return os.path.join(Constant.A_WORKING_DIR, self.dep_id)

    def _needs_cluster_network(self):
        if len(self.settings.roles) == 1:  # there is only 1 node
            return False
        if self.node_counts['storage'] > 1:  # at least 2 nodes have storage
            return True
        return False

    def has_suma(self):
        for roles in self.settings.roles:
            if 'suma' in roles:
                return True
        return False

    def __generate_static_networks(self):
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
        self.public_network_segment = "{}0/24".format(public_network)

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

    def __generate_nodes(self):
        node_id = 0
        worker_id = 0
        loadbl_id = 0
        nfs_id = 0
        Log.debug("__generate_nodes: about to process cluster roles: {}"
                  .format(self.settings.roles))

        for node_roles in self.settings.roles:  # loop once for every node in cluster
            if self.settings.version == 'caasp4':
                if 'master' in node_roles:
                    node_id += 1
                    name = 'master'
                    fqdn = 'master.{}'.format(self.domain)
                elif 'worker' in node_roles:
                    worker_id += 1
                    node_id += 1
                    name = 'worker{}'.format(worker_id)
                    fqdn = 'worker{}.{}'.format(worker_id, self.domain)
                elif 'loadbalancer' in node_roles:
                    loadbl_id += 1
                    node_id += 1
                    name = 'loadbl{}'.format(loadbl_id)
                    fqdn = 'loadbl{}.{}'.format(loadbl_id, self.domain)
                elif 'nfs' in node_roles and self.settings.version == 'caasp4':
                    nfs_id += 1
                    node_id += 1
                    name = 'nfs{}'.format(nfs_id)
                    fqdn = 'nfs{}.{}'.format(nfs_id, self.domain)
                else:
                    node_id += 1
                    name = 'node{}'.format(node_id)
                    fqdn = 'node{}.{}'.format(node_id, self.domain)
            else:
                if 'master' in node_roles or 'suma' in node_roles or 'makecheck' in node_roles:
                    name = 'master'
                    fqdn = 'master.{}'.format(self.domain)
                else:
                    node_id += 1
                    name = 'node{}'.format(node_id)
                    fqdn = 'node{}.{}'.format(node_id, self.domain)

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
                else:
                    public_address = '{}{}'.format(self.settings.public_network, 200 + node_id)
                networks = ('node.vm.network :private_network, autostart: true, ip:'
                            '"{}"').format(public_address)
                if self.settings.ipv6:
                    networks += ', libvirt__guest_ipv6: "yes"' \
                                ', libvirt__ipv6_address: "fde4:8dba:82e1::c4"' \
                                ', libvirt__ipv6_prefix: "64"'

            if 'bootstrap' in node_roles:
                self.bootstrap_mon_ip = public_address

            node = Node(name,
                        fqdn,
                        node_roles,
                        networks,
                        public_address=public_address,
                        ram=self.settings.ram * 2**10,
                        cpus=self.settings.cpus)

            for role in node_roles:
                self.nodes_with_role[role].append(name)

            self.roles_of_nodes[name] = node_roles

            if 'master' in node_roles:
                self.master = node

            if self.settings.version == 'caasp4':
                single_node = self.settings.single_node or len(self.settings.roles) == 1
                if 'master' in node_roles or 'worker' in node_roles:
                    node.cpus = max(node.cpus, 2)
                    if self.settings.ram < 2:
                        node.ram = 2 * 2**10
                if self.settings.caasp_deploy_ses or self.settings.explicit_num_disks:
                    if 'worker' in node_roles or single_node:
                        self.__append_disks_to_node(node)

            if self.settings.version in Constant.CORE_VERSIONS:
                if 'suma' in node_roles:
                    self.suma = node
                if 'storage' in node_roles:
                    if self.settings.cluster_network:
                        node.cluster_address = '{}{}'.format(self.settings.cluster_network,
                                                             200 + node_id)
                    self.__append_disks_to_node(node)
                elif self.settings.explicit_num_disks \
                        and not node.has_exactly_roles(['master', 'admin']):
                    self.__append_disks_to_node(node)

            if self.has_suma():  # if suma is deployed, we need to add client-tools to all nodes
                node.add_custom_repo(ZypperRepo(
                    name='suma_client_tools',
                    url='https://download.opensuse.org/repositories/systemsmanagement:/'
                        'Uyuni:/Master:/openSUSE_Leap_15-Uyuni-Client-Tools/openSUSE_Leap_15.0/'
                ))

            # from https://www.uyuni-project.org/uyuni-docs/uyuni/installation/install-vm.html
            if 'suma' in node_roles:
                if self.settings.ram < 4:
                    node.ram = 4096
                node.cpus = max(self.settings.cpus, 4)
                # disk for /var/spacewalk
                node.storage_disks.append(Disk(101))
                # disk for /var/lib/pgsql
                node.storage_disks.append(Disk(51))

                node.add_custom_repo(ZypperRepo(
                    name='suma_media1',
                    url='https://download.opensuse.org/repositories/systemsmanagement:/'
                        'Uyuni:/Master/images-openSUSE_Leap_15.1/repo/'
                        'Uyuni-Server-POOL-x86_64-Media1/'
                ))

            for repo_obj in self.settings.custom_repos:
                node.add_custom_repo(repo_obj)

            self.nodes[node.name] = node

    def __append_disks_to_node(self, node):
        for _i, _n in enumerate(self.settings.num_disks):
            for _ in range(_n):
                if len(self.settings.disk_size) > _i:
                    node.storage_disks.append(Disk(self.settings.disk_size[_i]))
                else:
                    node.storate.disks.append(Disk(Constant.DEFAULT_DISK_SIZE))

    def __set_version_devel_repos(self):
        try:
            version = self.settings.version
            os_setting = self.settings.os
            version_devel_repos = self.settings.version_devel_repos[version][os_setting]
            if version == 'nautilus':
                upgrade_devel_repos = self.settings.version_devel_repos['octopus']['leap-15.2']
            elif version == 'ses6':
                upgrade_devel_repos = self.settings.version_devel_repos['ses7']['sles-15-sp2']
            else:
                upgrade_devel_repos = []
        except KeyError as exc:
            raise VersionOSNotSupported(self.settings.version, self.settings.os) from exc
        #
        # version_repos might contain URLs with a "magic priority prefix" -- see
        # https://github.com/SUSE/sesdev/issues/162
        self.version_devel_repos = []
        for repo in version_devel_repos:
            version_devel_repos_dict = {}
            prio_match = re.match(r'^(\d.+)!(http.*)', repo)
            if prio_match:
                version_devel_repos_dict = {
                    "url": prio_match[2],
                    "priority": prio_match[1],
                }
            else:
                version_devel_repos_dict = {
                    "url": repo,
                    "priority": 0,
                }
            self.version_devel_repos.append(version_devel_repos_dict)
        self.upgrade_devel_repos = upgrade_devel_repos
        Log.debug("_set_version_devel_repos: self.version_devel_repos: {}"
                  .format(self.version_devel_repos))

    def __set_os_base_repos(self):
        if self.settings.os in self.settings.os_repos:
            self.os_base_repos = list(self.settings.os_repos[self.settings.os].items())
        else:
            self.os_base_repos = []
        if self.settings.version == 'nautilus':
            self.os_upgrade_repos = list(Constant.OPENSUSE_REPOS['leap-15.2'].items())
        elif self.settings.version == 'ses6':
            self.os_upgrade_repos = list(self.settings.os_repos['sles-15-sp2'].items())
        else:
            self.os_upgrade_repos = []

    def __set_os_ca_repo(self):
        if self.settings.os in self.settings.os_ca_repo:
            self.os_ca_repo = self.settings.os_ca_repo[self.settings.os]
        else:
            self.os_ca_repo = None

    def __set_internal_media_repo(self):
        if self.settings.version in self.settings.internal_media_repos:
            self.internal_media_repo = \
                self.settings.internal_media_repos[self.settings.version].items()

    def __set_developer_tools_repos(self):
        if self.settings.os in self.settings.developer_tools_repos:
            self.developer_tools_repos = \
                list(
                    self.settings.developer_tools_repos[self.settings.os].items()
                )

    def __set_os_makecheck_repos(self):
        if self.settings.os in self.settings.os_makecheck_repos:
            self.os_makecheck_repos = \
                list(
                    self.settings.os_makecheck_repos[self.settings.os].items()
                )
        else:
            self.os_makecheck_repos = []

    def __analyze_ceph_salt_github_pr_fetching(self):
        self.ceph_salt_fetch_github_pr_heads = False
        self.ceph_salt_fetch_github_pr_merges = False
        ceph_salt_git_branch = self.settings.ceph_salt_git_branch
        if ceph_salt_git_branch and ceph_salt_git_branch.startswith('origin/pr/'):
            Log.info("Detected special ceph-salt GitHub PR (HEAD) branch {}"
                     .format(ceph_salt_git_branch)
                     )
            self.ceph_salt_fetch_github_pr_heads = True
        elif ceph_salt_git_branch and ceph_salt_git_branch.startswith('origin/pr-merged/'):
            Log.info("Detected special ceph-salt GitHub PR (MERGE) branch {}"
                     .format(ceph_salt_git_branch)
                     )
            self.ceph_salt_fetch_github_pr_merges = True

    def __set_cephadm_bootstrap_node(self):
        self.cephadm_bootstrap_node = None
        if self.nodes_with_role["bootstrap"]:
            self.cephadm_bootstrap_node = self.nodes[self.nodes_with_role["bootstrap"][0]]

    def _prepare_to_generate_vagrantfile(self):
        """
        Add some properties to the deployment object which are needed for new
        deployments
        """
        self.__set_version_devel_repos()
        self.__set_os_base_repos()
        self.__set_os_ca_repo()
        self.__set_internal_media_repo()
        self.__set_developer_tools_repos()
        self.__set_os_makecheck_repos()
        self.__analyze_ceph_salt_github_pr_fetching()
        self.__set_cephadm_bootstrap_node()

    def _generate_vagrantfile(self):
        self._prepare_to_generate_vagrantfile()

        context = {
            'ssh_key_name': Constant.SSH_KEY_NAME,
            'ssh_extra_key_ids': [key['keyid'] for key in self._extra_ssh_keys],
            'sesdev_path_to_qa': Constant.PATH_TO_QA,
            'dep_id': self.dep_id,
            'os': self.settings.os,
            'ram': self.settings.ram,
            'package_manager': Constant.OS_PACKAGE_MANAGER_MAPPING[self.settings.os],
            'vm_engine': self.settings.vm_engine,
            'libvirt_host': self.settings.libvirt_host,
            'libvirt_user': self.settings.libvirt_user,
            'libvirt_use_ssh': 'true' if self.settings.libvirt_use_ssh else 'false',
            'libvirt_private_key_file': self.settings.libvirt_private_key_file,
            'libvirt_storage_pool': self.settings.libvirt_storage_pool,
            'ipv6': self.settings.ipv6,
            'vagrant_box': self.vagrant_box,
            'nodes': list(self.nodes.values()),
            'cluster_json': json.dumps({
                "num_disks": self.settings.num_disks,
                "roles_of_nodes": self.roles_of_nodes,
                "cephadm_bootstrap_node": (self.cephadm_bootstrap_node.name if
                                           self.cephadm_bootstrap_node else ''),
                }, sort_keys=True, indent=4),
            'master': self.master,
            'suma': self.suma,
            'domain': self.domain,
            'deepsea_git_repo': self.settings.deepsea_git_repo,
            'deepsea_git_branch': self.settings.deepsea_git_branch,
            'version': self.settings.version,
            'provision': self.settings.provision,
            'deploy_salt': bool(self.settings.version != 'makecheck' and
                                self.settings.version != 'caasp4' and
                                not self.suma and
                                not self.settings.os.startswith('ubuntu')),
            'stop_before_stage': self.settings.stop_before_stage,
            'deployment_tool': self.settings.deployment_tool,
            'version_devel_repos': self.version_devel_repos,
            'os_base_repos': self.os_base_repos,
            'os_ca_repo': self.os_ca_repo,
            'os_makecheck_repos': self.os_makecheck_repos,
            'devel_repo': self.settings.devel_repo,
            'core_version': self.settings.version in Constant.CORE_VERSIONS,
            'qa_test': self.settings.qa_test,
            'node_list': self.node_list,
            'cephadm_bootstrap_node': self.cephadm_bootstrap_node,
            'prometheus_nodes': self.node_counts["prometheus"],
            'prometheus_node_list': ','.join(self.nodes_with_role["prometheus"]),
            'grafana_nodes': self.node_counts["grafana"],
            'grafana_node_list': ','.join(self.nodes_with_role["grafana"]),
            'alertmanager_nodes': self.node_counts["alertmanager"],
            'alertmanager_node_list': ','.join(self.nodes_with_role["alertmanager"]),
            'node_exporter_nodes': self.node_counts["node-exporter"],
            'node_exporter_node_list': ','.join(self.nodes_with_role["node-exporter"]),
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
            'worker_nodes': self.node_counts["worker"],
            'deepsea_need_stage_4': bool(self.node_counts["nfs"] or self.node_counts["igw"]
                                         or self.node_counts["mds"] or self.node_counts["rgw"]
                                         or self.node_counts["openattic"]),
            'total_osds': sum(self.settings.num_disks) * self.node_counts["storage"],
            'encrypted_osds': self.settings.encrypted_osds,
            'filestore_osds': self.settings.filestore_osds,
            'scc_username': self.settings.scc_username,
            'scc_password': self.settings.scc_password,
            'ceph_salt_git_repo': self.settings.ceph_salt_git_repo,
            'ceph_salt_git_branch': self.settings.ceph_salt_git_branch,
            'ceph_salt_fetch_github_pr_heads': self.ceph_salt_fetch_github_pr_heads,
            'ceph_salt_fetch_github_pr_merges': self.ceph_salt_fetch_github_pr_merges,
            'stop_before_ceph_salt_config': self.settings.stop_before_ceph_salt_config,
            'stop_before_ceph_salt_apply': self.settings.stop_before_ceph_salt_apply,
            'stop_before_ceph_orch_apply': self.settings.stop_before_ceph_orch_apply,
            'stop_before_cephadm_bootstrap': self.settings.stop_before_cephadm_bootstrap,
            'reg': self.settings.reg,
            'ceph_image_path': self.settings.ceph_image_path,
            'grafana_image_path': self.settings.grafana_image_path,
            'prometheus_image_path': self.settings.prometheus_image_path,
            'node_exporter_image_path': self.settings.node_exporter_image_path,
            'alertmanager_image_path': self.settings.alertmanager_image_path,
            'haproxy_image_path': self.settings.haproxy_image_path,
            'keepalived_image_path': self.settings.keepalived_image_path,
            'snmp_gateway_image_path': self.settings.snmp_gateway_image_path,
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
            'ssd': self.settings.ssd,
            'fqdn': self.settings.fqdn,
            'reasonable_timeout_in_seconds': Constant.REASONABLE_TIMEOUT_IN_SECONDS,
            'public_network': self.public_network_segment,
            'bootstrap_mon_ip': self.bootstrap_mon_ip,
            'msgr2_secure_mode': self.settings.msgr2_secure_mode,
            'msgr2_prefer_secure': self.settings.msgr2_prefer_secure,
            'upgrade_devel_repos': self.upgrade_devel_repos,
            'os_upgrade_repos': self.os_upgrade_repos,
            'apparmor': self.settings.apparmor,
            'rgw_ssl': self.settings.rgw_ssl,
            'internal_media_repo': self.internal_media_repo,
            'developer_tools_repos': self.developer_tools_repos,
        }

        scripts = {}

        for node in self.nodes.values():
            context_cpy = dict(context)
            context_cpy['node'] = node
            template = Constant.JINJA_ENV.get_template('provision.sh.j2')
            scripts['provision_{}.sh'.format(node.name)] = template.render(**context_cpy)

        template = Constant.JINJA_ENV.get_template('Vagrantfile.j2')
        scripts['Vagrantfile'] = template.render(**context)
        return scripts

    def save(self, log_handler):
        if self.settings.vm_engine == 'libvirt':
            self._get_vagrant_box(log_handler)
        else:
            raise UnsupportedVMEngine(self.settings.vm_engine)
        #
        # by "scripts", we mean the Vagrantfile itself plus one provisioning
        # script for each node
        scripts = self._generate_vagrantfile()
        key = RSA.generate(2048)
        private_key = key.exportKey('PEM')
        public_key = key.publickey().exportKey('OpenSSH')
        #
        # write settings to metadata file
        os.makedirs(self._dep_dir, exist_ok=False)
        metadata_file = os.path.join(self._dep_dir, Constant.METADATA_FILENAME)
        with open(metadata_file, 'w', encoding='utf-8') as file:
            json.dump({
                'id': self.dep_id,
                'settings': self.settings
            }, file, cls=SettingsEncoder)
        #
        # write "scripts" to files inside the _dep_dir
        for filename, script in scripts.items():
            full_path = os.path.join(self._dep_dir, filename)
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(script)
        #
        # generate and write deployment-specific ssh key pair
        keys_dir = os.path.join(self._dep_dir, 'keys')
        os.makedirs(keys_dir)
        priv_key = os.path.join(keys_dir, Constant.SSH_KEY_NAME)
        pub_key = f"{priv_key}.pub"
        with open(priv_key, 'wb') as file:
            file.write(private_key)
        os.chmod(priv_key, 0o600)
        with open(pub_key, 'wb') as file:
            file.write(public_key + b" sesdev\n")
        os.chmod(pub_key, 0o600)

        for key in self._extra_ssh_keys:
            path = os.path.join(keys_dir, "id_{}.pub".format(key['keyid']))
            with open(path, 'w', encoding='utf-8') as file:
                file.write(key['keyline'])
            os.chmod(path, 0o600)

        #
        # create bin dir for helper scripts
        bin_dir = os.path.join(self._dep_dir, 'bin')
        os.makedirs(bin_dir)

    def _get_vagrant_box(self, log_handler):
        Log.debug('_get_vagrant_box: os is ->{}<'.format(self.settings.os))
        if self.settings.os in Constant.OS_BOX_ALIASES:
            self.vagrant_box = Constant.OS_BOX_ALIASES[self.settings.os]
        else:
            self.vagrant_box = self.settings.os
        Log.debug('_get_vagrant_box: vagrant_box is ->{}<-'.format(self.vagrant_box))
        assert self.vagrant_box in self.box.all_possible_boxes, \
            "self.vagrant_box got set to unrecognized value ->{}<-".format(self.vagrant_box)
        #
        Log.info("Checking if vagrant box is already here: {}" .format(self.vagrant_box))
        found_box = False
        cmd = ['vagrant', 'box', 'list']
        output = tools.run_sync(cmd)
        lines = output.split('\n')
        for line in lines:
            if line:
                box_name = line.split()[0]
                if box_name == self.vagrant_box:
                    Log.info("Found vagrant box")
                    found_box = True
                    break
        if not found_box:
            Log.info("Vagrant box for OS ->{}<- is not installed: downloading it"
                     .format(self.settings.os))
            log_handler("Downloading vagrant box: {}\n".format(self.vagrant_box))
            #
            # remove image in libvirt to guarantee that, when "vagrant up"
            # runs, the new box will be uploaded to libvirt
            image_to_remove = self.box.get_image_by_box(self.vagrant_box)
            if image_to_remove:
                self.box.remove_image(image_to_remove)
            #
            # trigger "vagrant box add"
            box_path = None
            cmd = ["vagrant", "box", "add", "--provider", "libvirt"]
            if self.vagrant_box in Constant.OS_ALIASED_BOXES:
                # official vagrant boxes from vagrant cloud have name hard-coded
                box_path = self.vagrant_box
            else:
                cmd += ["--name", self.settings.os]
                if self.settings.os in self.settings.os_box:
                    box_path = self.settings.os_box[self.settings.os]
                else:
                    box_path = Constant.OS_BOX_MAPPING[self.settings.os]
            cmd += [box_path]
            tools.run_async(cmd, log_handler)

    def _vagrant_up(self, node, log_handler):
        cmd = ["vagrant", "up", "--no-destroy-on-error"]
        if self.existing:
            cmd.extend(["--no-provision"])
        else:
            cmd.extend(["--provision"])
        if node is not None:
            cmd.append(node)
        if Constant.VAGRANT_DEBUG:
            cmd.append('--debug')
        tools.run_async(cmd, log_handler, self._dep_dir)

    def reboot_one_node(self, log_handler, node):
        if node not in self.nodes:
            raise NodeDoesNotExist(node, self.dep_id)
        log_handler("=> running 'reboot' via SSH on node '{}'\n".format(node))
        ssh_cmd = ("bash -x -c 'reboot'",)
        retval = self.ssh(node, ssh_cmd, False)
        log_handler("=> interactive SSH command returned {}\n".format(retval))
        seconds_to_wait = 600
        log_handler("=> waiting up to {} seconds for node '{}' to come back from reboot\n"
                    .format(seconds_to_wait, node)
                   )
        interval_seconds = 15
        while True:
            ssh_cmd = ("bash -x -c 'echo I am back'",)
            retval = self.ssh(node, ssh_cmd, False)
            if retval == 0:
                break
            log_handler("=> interactive SSH command returned {}\n".format(retval))
            seconds_to_wait -= interval_seconds
            if seconds_to_wait <= 0:
                log_handler("ERROR: node '{}' did not come back from reboot!\n".format(node))
                raise RebootDidNotSucceed(node, self.dep_id)
            log_handler("=> waiting up to {} more seconds for node '{}' to come back from reboot\n"
                        .format(seconds_to_wait, node)
                       )
            time.sleep(interval_seconds)
        log_handler("=> node '{}' is back from reboot!\n".format(node))
        seconds_to_wait = 600
        log_handler("=> waiting up to {} seconds for node '{}' to finish booting\n"
                    .format(seconds_to_wait, node)
                   )
        while True:
            ssh_cmd = ("bash -x -c 'systemctl is-system-running'",)
            retval = self.ssh(node, ssh_cmd, False)
            if retval == 0:
                break
            log_handler("=> interactive SSH command returned {}\n".format(retval))
            seconds_to_wait -= interval_seconds
            if seconds_to_wait <= 0:
                log_handler("ERROR: node '{}' did not complete boot sequence!\n".format(node))
                raise RebootDidNotSucceed(node, self.dep_id)
            log_handler("=> waiting up to {} more seconds for node '{}' to finish booting\n"
                        .format(seconds_to_wait, node)
                       )
            time.sleep(interval_seconds)
        log_handler("=> node '{}' completed boot sequence!\n".format(node))

    def destroy(self, log_handler, destroy_networks=False):

        # if we are allowing networks to be destroyed, populate the networks
        # list; we will find all networks now, and we'll destroy them last.
        used_networks = []
        if destroy_networks:
            used_networks = self.box.get_networks_by_deployment(self.dep_id)

        Log.debug("should destroy networks: {}, networks: {}"
                  .format(destroy_networks, used_networks))

        errors_encountered = False
        cmd = ['vagrant', 'destroy', '--force']
        if Constant.VAGRANT_DEBUG:
            cmd.append('--debug')
        try:
            tools.run_sync(cmd, cwd=self._dep_dir)
        # pylint: disable=invalid-name
        except CmdException as e:
            errors_encountered = True
            saved_verbose_setting = Constant.VERBOSE
            Constant.VERBOSE = True
            Log.error("\"{}\" failed:\n{}".format(' '.join(cmd), e))
            Log.info("Falling back to node-by-node destroy")
            Constant.VERBOSE = saved_verbose_setting

        if errors_encountered:
            # fall back to node-by-node destroy
            for node in self.nodes.values():
                if node.status == 'not deployed':
                    continue
                cmd = ["vagrant", "destroy", node.name, "--force"]
                if Constant.VAGRANT_DEBUG:
                    cmd.append('--debug')
                try:
                    tools.run_async(cmd, log_handler, cwd=self._dep_dir)
                # pylint: disable=invalid-name
                except CmdException as e:
                    saved_verbose_setting = Constant.VERBOSE
                    Constant.VERBOSE = True
                    Log.error("\"{}\" failed:\n{}".format(' '.join(cmd), e))
                    Log.info("Forging on in spite of the error")
                    Constant.VERBOSE = saved_verbose_setting

        shutil.rmtree(self._dep_dir)
        # clean up any orphaned volumes
        images_to_remove = self.box.get_images_by_deployment(self.dep_id)
        if images_to_remove:
            Log.warning("Found orphaned volumes: {}".format(images_to_remove))
            Log.info("Removing orphaned volumes")
            for image in images_to_remove:
                self.box.remove_image(image)

        for network in used_networks:
            Log.info("Destroy network '{}'".format(network))
            if not self.box.destroy_network(network):
                Log.warning("Unable to destroy network '{}' for deployment '{}'"
                            .format(network, self.dep_id))
            else:
                Log.info("Destroyed network '{}' for deployment '{}'"
                         .format(network, self.dep_id))

        if errors_encountered:
            print("""
ERROR: deployment "{dep_id}" possibly not completely destroyed

sesdev did its best to destroy the deployment, but errors were
encountered. What this means is some parts of the deployment
might still be left over.

To check this, consider the following hints (which may or may not
work when run verbatim in your environment):

    sudo virsh list --all | grep '^ {dep_id}'
    sudo virsh vol-list default | grep '^ {dep_id}'
    sudo virsh net-list | grep '^ {dep_id}'
    (cd ~/.sesdev ; ls -d1 */ | grep '^{dep_id}')

If any of these show lines starting with "{dep_id}", the
deployment might not be completely destroyed.
""".format(dep_id=self.dep_id))

    def _stop(self, node):
        if self.nodes[node].status != "running":
            Log.warning("Node '{}' is not running: current status '{}'"
                        .format(node, self.nodes[node].status))
            return
        # Ugly hack to let ssh successfully exit before the connection is
        # dropped during VM shutdown:
        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(['echo "sleep 2 && shutdown -h now" > /root/shutdown.sh '
                        '&& chmod +x /root/shutdown.sh'])
        tools.run_sync(ssh_cmd)
        ssh_cmd = self._ssh_cmd(node)
        ssh_cmd.extend(['nohup /root/shutdown.sh > /dev/null 2>&1 &'])
        tools.run_sync(ssh_cmd)

        # Wait up to one minute for node to actually shut down:
        for _ in range(12):
            self.load_status()

            if self.nodes[node].status == "stopped":
                Log.info(f"Node {node} successfully stopped.")
                break

            time.sleep(5)

    def stop(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise NodeDoesNotExist(node, self.dep_id)
        if node:
            log_handler("Stopping node {} of deployment {}\n".format(node, self.dep_id))
            self._stop(node)
        else:
            for _node in self.nodes:
                log_handler("Stopping node {} of deployment {}\n".format(_node, self.dep_id))
                self._stop(_node)

    def start(self, log_handler, node=None):
        if node and node not in self.nodes:
            raise NodeDoesNotExist(node, self.dep_id)
        if not self.existing:
            assert self.vagrant_box is not None, "vagrant_box is set to None!"
        self._vagrant_up(node, log_handler)

    def __str__(self):
        return self.dep_id

    def load_status(self):
        if not os.path.exists(os.path.join(self._dep_dir, '.vagrant')):
            for node in self.nodes.values():
                node.status = "not deployed"
            return

        cmd = ['vagrant', 'status']
        out = tools.run_sync(cmd, cwd=self._dep_dir)
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

    def configuration_report(self,
                             show_deployment_wide_params=True,
                             show_individual_vms=False,
                             ):

        result = ""
        if show_deployment_wide_params:
            result += "\n"
            result += "Deployment-wide parameters (applicable to all VMs in deployment):\n"
            result += "\n"
            result += "- deployment ID:    {}\n".format(self.dep_id)
            result += "- number of VMs:    {}\n".format(len(self.nodes))
            result += "- version:          {}\n".format(self.settings.version)
            result += "- OS:               {}\n".format(self.settings.os)
            result += "- public network:   {}0/24\n".format(self.settings.public_network)
            if self.settings.version == 'makecheck':
                result += ("- git repo:         {}\n"
                           .format(self.settings.makecheck_ceph_repo))
                result += ("- git branch:       {}\n"
                           .format(self.settings.makecheck_ceph_branch))
            if self.settings.version in ['octopus', 'ses7', 'pacific', 'ses7p']:
                result += "- ceph_image_path:          {}\n".format(
                    self.settings.ceph_image_path)
                result += "- prometheus_image_path:    {}\n".format(
                    self.settings.prometheus_image_path)
                result += "- alertmanager_image_path:  {}\n".format(
                    self.settings.alertmanager_image_path)
                result += "- grafana_image_path:       {}\n".format(
                    self.settings.grafana_image_path)
                result += "- node_exporter_image_path: {}\n".format(
                    self.settings.node_exporter_image_path)
                result += "- haproxy_image_path:       {}\n".format(
                    self.settings.haproxy_image_path)
                result += "- keepalived_image_path:    {}\n".format(
                    self.settings.keepalived_image_path)
                result += "- snmp_gateway_image_path:  {}\n".format(
                    self.settings.snmp_gateway_image_path)
            for synced_folder in self.settings.synced_folder:
                result += "- synced_folder:    {}\n".format(' -> '.join(synced_folder))
            if self.settings.custom_repos:
                result += "- custom_repos"
                if self.settings.repo_priority:
                    result += " (with elevated priority):\n"
                else:
                    result += " (with default priority, because --repo-priority not given):\n"
                for repo in self.settings.custom_repos:
                    repo_obj = ZypperRepo(**repo)
                    result += "  - {}\n".format(repo_obj.url)
            if self.settings.version in Constant.CORE_VERSIONS:
                result += "- qa_test:          {}\n".format(self.settings.qa_test)
            if self.settings.fqdn:
                result += "- FQDN:             {}\n".format(self.settings.fqdn)
            if self.settings.rgw_ssl:
                result += "- RGW with SSL:     {}\n".format(self.settings.rgw_ssl)
            if self.settings.deepsea_git_repo and self.settings.deepsea_git_branch:
                result += "- DeepSea repo:     {}\n".format(self.settings.deepsea_git_repo)
                result += "- DeepSea branch:   {}\n".format(self.settings.deepsea_git_branch)
        if show_individual_vms:
            result += "\n"
            result += "Individual VM parameters:\n"
            result += "\n"
            for k, v in self.nodes.items():
                result += "  -- {}:\n".format(k)
                if v.status:
                    result += "     - status:           {}\n".format(v.status)
                result += "     - cpus:             {}\n".format(v.cpus)
                result += "     - ram:              {}G\n".format(int(v.ram / (2 ** 10)))
                if k == 'master':
                    result += "     - deployment_tool:  {}\n".format(self.settings.deployment_tool)
                result += "     - roles:            {}\n".format(v.roles)
                if 'storage' in v.roles:
                    result += "     - storage_disks:    {}\n".format(len(v.storage_disks))
                    result += ("                         "
                               "(device names will be assigned by vagrant-libvirt)\n")
                    result += "     - OSD encryption:   {}\n".format(
                        "Yes" if self.settings.encrypted_osds else "No")
                    result += "     - OSD objectstore:  {}\n".format(
                        "FileStore" if self.settings.filestore_osds else "BlueStore")
                if self.settings.version in ["octopus", "ses7", "pacific"]:
                    if 'admin' not in v.roles and v.roles != [] and v.roles != ['client']:
                        result += (
                            "                         (CAVEAT: the 'admin' role is assumed"
                            " even though not explicitly given!)\n"
                        )
                result += "     - fqdn:             {}\n".format(v.fqdn)
                if v.public_address:
                    result += "     - public_address:   {}\n".format(v.public_address)
                if v.cluster_address:
                    result += "     - cluster_address:  {}\n".format(v.cluster_address)
                result += "\n"
        return result

    def vet_configuration(self):
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
        # and bootstrap must have admin role as well (unless this is
        # merely a partial deployment - then we don't care)
        if self.settings.version in ['ses7', 'octopus', 'pacific']:
            if (not self.settings.stop_before_ceph_salt_config and
                not self.settings.stop_before_ceph_salt_apply
            ):
                if self.node_counts['bootstrap'] != 1:
                    raise UniqueRoleViolation('bootstrap', self.node_counts['bootstrap'])
                if (not self.settings.stop_before_ceph_salt_apply and
                    not self.settings.stop_before_ceph_orch_apply
                ):
                    for node_roles in self.settings.roles:
                        if 'master' in node_roles and 'admin' not in node_roles:
                            raise NodeMustBeAdminAsWell('master')
        # clusters with no OSDs can be deployed only in certain circumstances
        if self.settings.version in ['ses5', 'nautilus', 'ses6']:
            if self.node_counts['storage'] == 0:
                raise NoStorageRolesDeepsea(self.settings.version)
        if self.settings.version in ['octopus', 'ses7', 'pacific']:
            if self.node_counts['storage'] == 0:
                if self.node_counts['rgw'] > 0:
                    raise NoStorageRolesCephadm('rgw')
                if self.node_counts['igw'] > 0:
                    raise NoStorageRolesCephadm('igw')
                if self.node_counts['nfs'] > 0:
                    raise NoStorageRolesCephadm('nfs')
                if self.node_counts['mds'] > 0:
                    raise NoStorageRolesCephadm('mds')
        # ganesha role only allowed pre-octopus
        if self.settings.version in ['octopus', 'ses7', 'pacific']:
            if self.node_counts["ganesha"] > 0:
                raise NoGaneshaRolePostNautilus()
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
        # --product makes sense only with SES
        if not self.settings.devel_repo and not self.settings.version.startswith('ses'):
            raise ProductOptionOnlyOnSES(self.settings.version)
        # caasp4 is special
        if self.settings.version in ['caasp4']:
            each_machine_has_one_and_only_one_role = True
            for node_roles in self.settings.roles:
                if len(node_roles) > 1:
                    each_machine_has_one_and_only_one_role = False
            if each_machine_has_one_and_only_one_role:
                Log.debug('caasp4 cluster: each machine has one and only one role. Good.')
            else:
                raise MultipleRolesPerMachineNotAllowedInCaaSP()
        else:
            # worker and loadbalancer only in caasp4
            if self.node_counts['worker'] > 0:
                raise RoleNotSupported('worker', self.settings.version)
            if self.node_counts['loadbalancer'] > 0:
                raise RoleNotSupported('loadbalancer', self.settings.version)
        # experimental Ubuntu Bionic
        if self.settings.os == 'ubuntu-bionic':
            if self.settings.version in ['octopus']:
                pass  # we support
            else:
                raise VersionOSNotSupported(
                                            self.settings.os,
                                            self.settings.version
                                            )
        # no node may have more than one of any role
        for node in self.settings.roles:
            for role in Constant.ROLES_KNOWN:
                if node.count(role) > 1:
                    raise DuplicateRolesNotSupported(role)

    def _vagrant_ssh_config(self, name):
        if name not in self.nodes:
            raise NodeDoesNotExist(name, self.dep_id)

        cmd = ["vagrant", "ssh-config", name]
        out = tools.run_sync(cmd, cwd=self._dep_dir)

        address = None
        proxycmd = None
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('HostName'):
                address = line[len('HostName') + 1:]
            elif line.startswith('ProxyCommand'):
                proxycmd = line[len('ProxyCommand') + 1:]

        if address is None:
            raise VagrantSshConfigNoHostName(name)

        dep_private_key = os.path.join(self._dep_dir, str("keys/" + Constant.SSH_KEY_NAME))

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
                " -o 'LogLevel=ERROR'"
            )
        else:
            retval = [
                "-o", "IdentitiesOnly yes",
                "-o", "StrictHostKeyChecking no",
                "-o", "UserKnownHostsFile /dev/null",
                "-o", "PasswordAuthentication no",
                "-o", "LogLevel ERROR",
            ]
        return retval

    def _ssh_cmd(self, name, command=None):
        # type: (str, Iterable[str]) -> List[str]
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
        Log.info("_ssh_cmd: {}".format(_cmd))
        return _cmd

    def ssh(self, name, command, interactive):
        if interactive:
            return tools.run_interactive(self._ssh_cmd(name, command))

        try:
            out = tools.run_sync(self._ssh_cmd(name, command))
            print("{}".format(out))
            return_code = 0
        except CmdException as excp:
            Log.info("Command {} not successful".format(command))
            return_code = excp.retcode
        return return_code

    def sync_ssh(self, name, command):
        # type: (str, Iterable[str]) -> str
        return tools.run_sync(
            self._ssh_cmd(name, command),
            self._dep_dir
        )

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
            Log.debug(log_msg)
        else:
            raise SupportconfigOnlyOnSLE()
        log_handler("=> Running supportconfig on deployment ID: {} (OS: {})\n".format(
            self.dep_id,
            self.settings.os
        ))
        ssh_cmd = ('timeout', '1h', 'supportconfig',)
        self.ssh(name, ssh_cmd, False)
        log_handler("=> Grabbing the resulting tarball from the cluster node\n")
        ssh_cmd = ('ls', '/var/log/scc*')
        scc_exists = self.ssh(name, ssh_cmd, False)
        ssh_cmd = ('ls', 'var/log/nts*')
        nts_exists = self.ssh(name, ssh_cmd, False)
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
        ssh_cmd = ('rm', '/var/log/{}'.format(glob_to_get),)
        self.ssh(name, ssh_cmd, False)

    def user_provision(self, node=None):
        custom_provision_dir = os.path.join(Constant.A_WORKING_DIR, '.user_provision')

        def copy_root_home_config(node):
            """Copy files from ~/.sesdev/.user_provision/config/* to /root on the VM"""
            custom_config_dir = os.path.join(custom_provision_dir, 'config')
            if not os.path.exists(custom_config_dir):
                msg = '{} does not exist, not copying any custom configs'
                Log.info(msg.format(custom_config_dir))
                return
            Log.info("=> Copying {} to {}:/root/".format(custom_provision_dir, node))
            self.rsync(
                '{}/'.format(custom_config_dir),
                '{}:/root/'.format(node),
                recurse=True,
            )

        def call_provision_script(node):
            """Copy ~/.sesdev/.user_provision/provision.sh on the VM and run it"""
            provision_script = os.path.join(custom_provision_dir, 'provision.sh')
            tmp_dir = '/tmp'
            target_path = '{}/provision.sh'.format(tmp_dir)
            if not os.path.exists(provision_script):
                msg = "{} does not exist, not running custom provisioning"
                Log.info(msg.format(provision_script))
                return
            Log.info("=> Copying {} to {}:{}".format(provision_script, node, target_path))
            self.rsync(
                provision_script,
                '{}:{}/'.format(node, tmp_dir),
            )
            Log.info("=> Executing {}".format(target_path))
            self.sync_ssh(node, ('bash', target_path))

        if not os.path.exists(custom_provision_dir):
            print("nothing to provision, {} does not exist".format(custom_provision_dir))
            return

        nodes = [node] if node else self.nodes
        for _node in nodes:
            copy_root_home_config(_node)
            call_provision_script(_node)

    def upgrade(self, log_handler, node, devel_repos=True, to_version='octopus'):
        if node not in self.nodes:
            raise NodeDoesNotExist(node, self.dep_id)
        from_version = self.settings.version
        if devel_repos:
            devel_product = 'devel'
        else:
            devel_product = 'product'
        version_combo_ok = False
        if from_version == 'nautilus' and to_version == 'octopus':
            version_combo_ok = True
        if from_version == 'ses6' and to_version == 'ses7':
            version_combo_ok = True
        if version_combo_ok:
            tools.run_async(
                ["vagrant", "provision", node, "--provision-with",
                 'upgrade-from-{}-to-{}-{}'.format(from_version, to_version, devel_product)],
                log_handler,
                self._dep_dir
            )
        else:
            raise UpgradeNotSupported(from_version, to_version)

    def qa_test(self, log_handler):
        tools.run_async(
            ["vagrant", "provision", "--provision-with", "qa-test"],
            log_handler,
            self._dep_dir
        )

    def add_repo_subcommand(self, custom_repo, update, log_handler):
        if self.settings.version in Constant.CORE_VERSIONS:
            pass
        else:
            raise SubcommandNotSupportedInVersion('add-repo', self.settings.version)
        if custom_repo:
            for node_name in self.nodes:
                priority_opt = ''
                if custom_repo.priority:
                    priority_opt = "--priority={} ".format(custom_repo.priority)
                self.ssh(
                    node_name,
                    (
                        "zypper --non-interactive addrepo --no-gpgcheck --refresh {}{} {}"
                        .format(priority_opt, custom_repo.url, custom_repo.name)
                    ).split(),
                    False
                )
        else:  # no repo given explicitly: use "devel" repo
            provision_target = "add-devel-repo-and-update" if update else "add-devel-repo"
            tools.run_async(
                ["vagrant", "provision", "--provision-with", provision_target],
                log_handler,
                self._dep_dir
            )

    def _find_service_node(self, service):
        if service in ['prometheus', 'grafana'] and self.settings.version == 'ses5':
            return 'master'
        nodes = [name for name, node in self.nodes.items() if service in node.roles]
        return nodes[0] if nodes else None

    def _find_node_by_address(self, address):
        for name, node in self.nodes.items():
            if node.has_address(address):
                return name
        return None

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
                try:
                    raw_json = tools.run_sync(ssh_cmd)
                    raw_json = raw_json.strip()
                    Log.debug("Got output: {}".format(raw_json))
                    decoded_json = json.loads(raw_json)
                    Log.debug("Decoded json: {}".format(decoded_json))
                    dashboard_url = decoded_json['dashboard']
                    Log.debug("Dashboard URL: {}".format(dashboard_url))
                    dashboard_address = re.match(
                        r"https://([^:]+)", dashboard_url).group(1)
                    node = self._find_node_by_address(dashboard_address)
                    if not node and dashboard_address:
                        node = re.match(r"^([^.]+)", dashboard_address).group(1)
                    Log.debug("Extracted node: {}".format(node))
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
                if self.settings.version in ['octopus', 'ses6', 'ses7p', 'pacific']:
                    remote_port = 9095
                    local_port = 9095
                else:
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
                raise NodeDoesNotExist(node, self.dep_id)
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

        ssh_cmd = self._ssh_cmd(master_node)
        ssh_cmd.append("salt-run saltutil.sync_runners")
        tools.run_sync(ssh_cmd)

    def replace_mgr_modules(self, local=None, pr=None, branch=None, repo=None, langs=None):
        if self.settings.version in ['nautilus', 'ses6', 'octopus', 'ses7', 'ses7p', 'pacific']:
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
        all_nodes = []
        mgr_nodes = []

        for _node in self.nodes.values():
            all_nodes.append(_node.name)
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
        # Fetch mgr modules
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
                zypper -n in python3-pip && \
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

        # Fetch bin/cephadm
        if self.settings.deployment_tool == 'cephadm':
            if local:
                local_cephadm_path = "{}/src/cephadm".format(local)
                master_cephadm_path = "/root/local/ceph/src/cephadm"

                ssh_cmd = self._ssh_cmd(master_node)
                ssh_cmd.append("rm -rf {0} && mkdir -p {0}".format(master_cephadm_path))
                tools.run_sync(ssh_cmd)

                self.rsync('{}/cephadm'.format(local_cephadm_path),
                           '{}:{}'.format(master_node, '{}/cephadm'.format(master_cephadm_path)))
            else:
                master_cephadm_path = "/root/remote/ceph/src/cephadm"

        for node in all_nodes:

            # Copy bin/cephadm
            if self.settings.deployment_tool == 'cephadm':
                ssh_cmd = self._ssh_cmd(node)
                ssh_cmd.append('podman ps --format "{}" -f label=ceph=True'.format("{{.ID}}"))
                containers = tools.run_sync(ssh_cmd)
                containers = containers.strip()
                containers = containers.split('\n') if containers else []

                print("Copying cephadm to node {}".format(node))
                ssh_cmd = self._ssh_cmd(master_node)
                ssh_cmd.append("scp {}/cephadm {}:/usr/sbin/cephadm"
                               .format(master_cephadm_path, node))
                tools.run_sync(ssh_cmd)

                for container in containers:
                    print("Copying cephadm to the container {}".format(container))
                    ssh_cmd = self._ssh_cmd(node)
                    ssh_cmd.append("podman cp /usr/sbin/cephadm {}:/usr/sbin/cephadm"
                                   .format(container))
                    tools.run_sync(ssh_cmd)

            if node not in mgr_nodes:
                continue

            # Copy mgr modules
            if self.settings.version in ['nautilus', 'ses6']:
                print("Copying mgr modules to node {}".format(node))
                ssh_cmd = self._ssh_cmd(master_node)
                ssh_cmd.append("scp -r {}/mgr/ {}:/usr/share/ceph/"
                               .format(master_path, node))
                tools.run_sync(ssh_cmd)
            else:

                ssh_cmd = self._ssh_cmd(node)
                ssh_cmd.append('podman ps --format "{}" -f name=mgr.{}'.format("{{.ID}}", node))
                containers = tools.run_sync(ssh_cmd)
                containers = containers.strip()
                containers = containers.split('\n') if containers else []

                print("Copying mgr modules to node {}".format(node))
                ssh_cmd = self._ssh_cmd(node)
                ssh_cmd.append("rm -rf ~/mgr")
                tools.run_sync(ssh_cmd)

                ssh_cmd = self._ssh_cmd(master_node)
                ssh_cmd.append("scp -r {}/mgr/ {}:~/".format(master_path, node))
                tools.run_sync(ssh_cmd)

                for container in containers:
                    print("Copying mgr modules to the container {}".format(container))
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

    def list_packages(self, repos=None):
        """
        Compile a list of packages installed on each host of the cluster.
        Return a dictionary by host to the list of packages installed on that
        host.
        Optionally takes a list of repos. When that list is non-empty, only
        packages installed from those repos will be included in the lists.
        """
        def _to_package_list(raw):
            lines = raw.splitlines()
            package_list = []

            for line in lines:
                cols = line.split()
                if len(cols) > 0 and (cols[0] == 'i' or cols[0] == 'i+'):
                    package_list.append(ZypperPackage(name=cols[2],
                                                      version=cols[3],
                                                      arch=cols[4],
                                                      state=cols[0],
                                                      repo=cols[1]))

            return package_list

        zypper_cmd = "zypper -t -s 11 pa -N -R -i"

        if repos:
            for repo in repos:
                zypper_cmd += f" -r {repo}"

        packages = {}
        for node in self.nodes:
            ssh_cmd = self._ssh_cmd(node)
            ssh_cmd.append(zypper_cmd)
            raw_package_list = tools.run_sync(ssh_cmd)

            packages[node] = _to_package_list(raw_package_list)

        return packages

    # This is the "real" constructor
    @classmethod
    def create(cls, dep_id, log_handler, settings):
        dep_dir = os.path.join(Constant.A_WORKING_DIR, dep_id)
        if os.path.exists(dep_dir):
            raise DeploymentAlreadyExists(dep_id)
        dep = cls(dep_id, settings)
        Log.info("creating new deployment: {}".format(dep))
        dep.save(log_handler)
        return dep

    @classmethod
    def load(cls, dep_id, load_status=True) -> 'Deployment':
        dep_dir = os.path.join(Constant.A_WORKING_DIR, dep_id)
        if not os.path.exists(dep_dir) or not os.path.isdir(dep_dir):
            Log.debug("->{}<- does not exist or is not a directory"
                      .format(dep_dir))
            raise DeploymentDoesNotExists(dep_id)

        metadata_file = os.path.join(dep_dir, Constant.METADATA_FILENAME)
        if not os.path.exists(metadata_file) or not os.path.isfile(metadata_file):
            Log.debug("metadata file ->{}<- does not exist or is not a file"
                      .format(metadata_file))
            raise DeploymentDoesNotExists(dep_id)
        with open(metadata_file, 'r', encoding='utf-8') as file:
            metadata = json.load(file)
        try:
            dep = cls(metadata['id'], Settings(strict=False, **metadata['settings']), existing=True)
            if load_status:
                dep.load_status()
            return dep

        except (AttributeError, TypeError) as error:
            Log.debug(error)
            raise DeploymentIncompatible(dep_id) from error

    @classmethod
    def list(cls, load_status=False) -> List['Deployment']:
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        Log.debug("Entering deployment.list (called from ->{}<-)".format(calframe[1][3]))
        deps = []
        if not os.path.exists(Constant.A_WORKING_DIR):
            return deps
        dir_listing = os.listdir(Constant.A_WORKING_DIR)
        Log.debug("Listing of directory {}: {}".format(
            Constant.A_WORKING_DIR,
            dir_listing))
        for dep_id in dir_listing:
            Log.debug("Considering deployment ->{}<-".format(dep_id))
            full_path = os.path.join(Constant.A_WORKING_DIR, dep_id)
            if not os.path.isdir(full_path):
                Log.debug("Skipping ->{}<- (obviously not a deployment)".format(dep_id))
                continue
            try:
                deps.append(Deployment.load(dep_id, load_status))
            except DeploymentDoesNotExists:
                continue
            except DeploymentIncompatible:
                Log.warning(
                    f'Deployment {dep_id} is incompatible with the current version of sesdev'
                )
        return deps
