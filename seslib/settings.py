import json
import os
import yaml

from .constant import Constant
from .exceptions import \
                        SettingNotKnown, \
                        SettingTypeError
from .log import Log

SETTINGS = {
    # RESERVED KEY, DO NOT USE: 'strict'
    'apparmor': {
        'type': bool,
        'help': 'Enable/disable AppArmor',
        'default': True,
    },
    'caasp_deploy_ses': {
        'type': bool,
        'help': 'Deploy SES using rook in CaasP',
        'default': False,
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
    'cluster_network': {
        'type': str,
        'help': 'The network address prefix for the cluster network',
        'default': '',
    },
    'container_registry': {
        'type': dict,
        'help': 'Container registry data [prefix, location, insecure]',
        'default': None,
    },
    'cpus': {
        'type': int,
        'help': 'Number of virtual CPUs in each node',
        'default': 2,
    },
    'custom_repos': {
        'type': list,
        'help': 'Optional custom zypper repos to apply to all nodes',
        'default': [],
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
    'deployment_tool': {
        'type': str,
        'help': 'Deployment tool (deepsea, cephadm) to deploy the Ceph cluster',
        'default': '',
    },
    'devel_repo': {
        'type': bool,
        'help': 'Include "devel" zypper repo, if applicable',
        'default': True,
    },
    'developer_tools_repos': {
        'type': dict,
        'help': 'Developer Tools Module repos for various versions of SLE',
        'default': Constant.DEVELOPER_TOOLS_REPOS,
    },
    'disk_size': {
        'type': int,
        'help': 'Storage disk size in gigabytes',
        'default': 8,
    },
    'domain': {
        'type': str,
        'help': 'The domain name for nodes',
        'default': '{}.test',
    },
    'dry_run': {
        'type': bool,
        'help': 'Dry run (do not deploy any VMs)',
        'default': False,
    },
    'encrypted_osds': {
        'type': bool,
        'help': 'Whether OSDs should be deployed encrypted',
        'default': False,
    },
    'explicit_cpus': {
        'type': bool,
        'help': 'Whether --cpus was given on the command line',
        'default': False,
    },
    'explicit_num_disks': {
        'type': bool,
        'help': 'Whether --num-disks was given on the command line',
        'default': False,
    },
    'explicit_ram': {
        'type': bool,
        'help': 'Whether --ram was given on the command line',
        'default': False,
    },
    'fqdn': {
        'type': bool,
        'help': 'Whether \'hostname\' command returns FQDN or short hostname',
        'default': False,
    },
    'filestore_osds': {
        'type': bool,
        'help': 'Whether OSDs should be deployed with FileStore instead of BlueStore',
        'default': False,
    },
    'image_path': {
        'type': str,
        'help': 'Deprecated container image path for Ceph daemons.',
        'default': '',
    },
    'ceph_image_path': {
        'type': str,
        'help': 'Container image path for Ceph daemons',
        'default': '',
    },
    'grafana_image_path': {
        'type': str,
        'help': 'Container image path for Grafana daemons',
        'default': '',
    },
    'prometheus_image_path': {
        'type': str,
        'help': 'Container image path for Prometheus daemons',
        'default': '',
    },
    'node_exporter_image_path': {
        'type': str,
        'help': 'Container image path for Node-Exporter daemons',
        'default': '',
    },
    'alertmanager_image_path': {
        'type': str,
        'help': 'Container image path for Alertmanager daemons',
        'default': '',
    },
    'keepalived_image_path': {
        'type': str,
        'help': 'Container image path for Keepalived daemons',
        'default': '',
    },
    'haproxy_image_path': {
        'type': str,
        'help': 'Container image path for HAProxy daemons',
        'default': '',
    },
    'image_paths_devel': {
        'type': dict,
        'help': 'Paths to devel container images',
        'default': Constant.IMAGE_PATHS_DEVEL,
    },
    'image_paths_product': {
        'type': dict,
        'help': 'Paths to product container images',
        'default': Constant.IMAGE_PATHS_PRODUCT,
    },
    'internal_media_repos': {
        'type': dict,
        'help': 'Internal Media repos for various versions of SES',
        'default': Constant.INTERNAL_MEDIA_REPOS,
    },
    'ipv6': {
        'type': bool,
        'help': 'Configure IPv6 addresses. This option requires "Accept Router '
                'Advertisements" to be set to 2. You can change it by running '
                '"sysctl -w net.ipv6.conf.<if>.accept_ra=2" where '
                '<if> is the network interface used by libvirt for network '
                'forwarding, or "all" to apply to all interfaces.',
        'default': False
    },
    'libvirt_host': {
        'type': str,
        'help': 'Hostname/IP address of the libvirt host',
        'default': '',
    },
    'libvirt_networks': {
        'type': str,
        'help': 'Existing libvirt networks to use (single or comma separated list)',
        'default': '',
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
    'libvirt_use_ssh': {
        'type': bool,
        'help': 'Flag to control the use of SSH when connecting to the libvirt host',
        'default': None,
    },
    'libvirt_user': {
        'type': str,
        'help': 'Username to use to login into the libvirt host',
        'default': '',
    },
    'makecheck_ceph_branch': {
        'type': str,
        'help': 'Branch to check out for purposes of running "make check"',
        'default': '',
    },
    'makecheck_ceph_repo': {
        'type': str,
        'help': 'Repo from which to clone Ceph source code',
        'default': '',
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
    'makecheck_username': {
        'type': str,
        'help': 'Name of ordinary user that will run make check',
        'default': 'sesdev',
    },
    'non_interactive': {
        'type': bool,
        'help': 'Whether the user wants to be asked',
        'default': False,
    },
    'num_disks': {
        'type': int,
        'help': 'Number of additional disks in storage nodes',
        'default': 2,
    },
    'os': {
        'type': str,
        'help': 'openSUSE OS version (leap-15.1, tumbleweed, sles-12-sp3, or sles-15-sp1)',
        'default': '',
    },
    'os_makecheck_repos': {
        'type': dict,
        'help': 'repos to add to VMs in "makecheck" environments',
        'default': Constant.OS_MAKECHECK_REPOS,
    },
    'os_box': {
        'type': dict,
        'help': 'vagrant box to be used for a given operating system (os)',
        'default': Constant.OS_BOX_MAPPING,
    },
    'os_ca_repo': {
        'type': dict,
        'help': 'ca repo to add on all VMs of a given operating system (os)',
        'default': Constant.OS_CA_REPO,
    },
    'os_repos': {
        'type': dict,
        'help': 'repos to add on all VMs of a given operating system (os)',
        'default': Constant.OS_REPOS,
    },
    'provision': {
        'type': bool,
        'help': 'Whether to provision the VMs (e.g., deploy Ceph on them) after they are created',
        'default': True,
    },
    'public_network': {
        'type': str,
        'help': 'The network address prefix for the public network',
        'default': '',
    },
    'qa_test': {
        'type': bool,
        'help': 'Automatically run integration tests on the deployed cluster',
        'default': False,
    },
    'ram': {
        'type': int,
        'help': 'RAM size in gigabytes for each node',
        'default': 4,
    },
    'repo_priority': {
        'type': bool,
        'help': 'One or more zypper repos will have elevated priority',
        'default': True,
    },
    'repos': {
        'type': list,
        'help': 'DEPRECATED: use custom_repos instead',
        'default': [],
    },
    'rgw_ssl': {
        'type': bool,
        'help': 'Whether to deploy RGW with SSL enabled',
        'default': False,
    },
    'roles': {
        'type': list,
        'help': 'Roles to apply to the current deployment',
        'default': [],
    },
    'scc_password': {
        'type': str,
        'help': 'SCC organization password',
        'default': '',
    },
    'scc_username': {
        'type': str,
        'help': 'SCC organization username',
        'default': '',
    },
    'single_node': {
        'type': bool,
        'help': 'Whether --single-node was given on the command line',
        'default': False,
    },
    'ssd': {
        'type': bool,
        'help': 'Makes one of the additional disks be non-rotational',
        'default': False,
    },
    'stop_before_ceph_orch_apply': {
        'type': bool,
        'help': 'Stops deployment before ceph orch apply',
        'default': False,
    },
    'stop_before_ceph_salt_apply': {
        'type': bool,
        'help': 'Stops deployment before ceph-salt apply',
        'default': False,
    },
    'stop_before_cephadm_bootstrap': {
        'type': bool,
        'help': 'Stops deployment before cephadm bootstrap',
        'default': False,
    },
    'stop_before_ceph_salt_config': {
        'type': bool,
        'help': 'Stops deployment before ceph-salt config',
        'default': False,
    },
    'stop_before_stage': {
        'type': int,
        'help': 'Stop deployment before running the specified DeepSea stage',
        'default': None,
    },
    'synced_folder': {
        'type': list,
        'help': 'Sync Folders to VM',
        'default': [],
    },
    'use_salt': {
        'type': bool,
        'help': 'Use "salt" (or "salt-run") to apply Salt Formula (or execute DeepSea Stages)',
        'default': False,
    },
    'version': {
        'type': str,
        'help': 'Deployment version to install ("nautilus", "ses6", "caasp4", etc.)',
        'default': 'nautilus',
    },
    'version_default_roles': {
        'type': dict,
        'help': 'Default roles for each node - one set of default roles per deployment version',
        'default': Constant.ROLES_DEFAULT_BY_VERSION,
    },
    'version_devel_repos': {
        'type': dict,
        'help': 'the "devel repo", whatever that means on a particular VERSION:OS combination',
        'default': Constant.VERSION_DEVEL_REPOS,
    },
    'version_os_repo_mapping': {
        'type': dict,
        'help': 'DEPRECATED: additional repos to be added on particular VERSION:OS combinations',
        'default': Constant.VERSION_DEVEL_REPOS,
    },
    'vm_engine': {
        'type': str,
        'help': 'VM engine to use for VM deployment. Current options [libvirt]',
        'default': 'libvirt',
    },
    'msgr2_secure_mode': {
        'type': bool,
        'help': 'Set "ms_*_mode" options to "secure"',
        'default': False,
    },
    'msgr2_prefer_secure': {
        'type': bool,
        'help': 'Prioritise secure mode over "crc" in the ms_*_mode options.',
        'default': False,
    },
}


class Settings():
    # pylint: disable=no-member
    def __init__(self, strict=True, **kwargs):
        self.strict = strict
        config = self._load_config_file()

        self._apply_settings(config)
        self._apply_settings(kwargs)

        for k, v in SETTINGS.items():
            if k not in kwargs and k not in config:
                Log.debug("Setting {} to default value ->{}<-"
                          .format(k, v['default']))
                setattr(self, k, v['default'])

    def override(self, setting, new_value):
        if setting not in SETTINGS:
            raise SettingNotKnown(setting)
        Log.debug("Overriding setting '{}', old value: {}"
                  .format(setting, getattr(self, setting)))
        Log.debug("Overriding setting '{}', new value: {}"
                  .format(setting, new_value))
        setattr(self, setting, new_value)

    def _apply_settings(self, settings_dict):
        for k, v in settings_dict.items():
            if k not in SETTINGS:
                if self.strict:
                    raise SettingNotKnown(k)
                Log.warning("Setting '{}' is not known - listing a legacy cluster?"
                            .format(k))
                continue
            if v is not None and not isinstance(v, SETTINGS[k]['type']):
                Log.error("Setting '{}' value has wrong type: expected ->{}<- but got ->{}<-"
                          .format(k, SETTINGS[k]['type'], type(v)))
                raise SettingTypeError(k, SETTINGS[k]['type'], v)
            setattr(self, k, v)

    @staticmethod
    def _load_config_file():

        config_tree = {}

        def _fill_in_config_tree(config_param, global_param):
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

        if not os.path.exists(Constant.CONFIG_FILE) \
                or not os.path.isfile(Constant.CONFIG_FILE):
            return config_tree

        with open(Constant.CONFIG_FILE, 'r', encoding='utf-8') as file:
            config_tree = yaml.safe_load(file) or {}
        Log.debug("_load_config_file: config_tree: {}".format(config_tree))
        assert isinstance(config_tree, dict), "yaml.load() of config file misbehaved!"
        _fill_in_config_tree('os_repos', Constant.OS_REPOS)
        _fill_in_config_tree('version_devel_repos', Constant.VERSION_DEVEL_REPOS)
        _fill_in_config_tree('image_paths_devel', Constant.IMAGE_PATHS_DEVEL)
        _fill_in_config_tree('image_paths_product', Constant.IMAGE_PATHS_PRODUCT)
        _fill_in_config_tree('version_default_roles', Constant.ROLES_DEFAULT_BY_VERSION)
        return config_tree


class SettingsEncoder(json.JSONEncoder):
    # pylint: disable=method-hidden
    def default(self, o):
        return {k: getattr(o, k) for k in SETTINGS}
