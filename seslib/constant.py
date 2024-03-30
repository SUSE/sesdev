import os

from pathlib import Path
from jinja2 import Environment, PackageLoader


class Constant():

    A_WORKING_DIR = os.path.join(Path.home(), '.sesdev')

    CEPH_SALT_REPO = 'https://github.com/ceph/ceph-salt'

    CEPH_SALT_BRANCH = 'master'

    CONFIG_FILE = os.path.join(A_WORKING_DIR, 'config.yaml')

    CORE_VERSIONS = ['nautilus', 'ses6', 'octopus', 'ses7', 'ses7p', 'pacific']

    DEBUG = False

    DEEPSEA_REPO = "https://github.com/SUSE/DeepSea"

    DEVELOPER_TOOLS_REPOS = {
        'sles-15-sp1': {
            'dev-tools': 'http://dist.suse.de/ibs/SUSE/Products/'
                         'SLE-Module-Development-Tools/15-SP1/x86_64/product/',
            'dev-tools-update': 'http://dist.suse.de/ibs/SUSE/Products/'
                                'SLE-Module-Development-Tools/15-SP1/x86_64/product/',
        },
        'sles-15-sp2': {
            'dev-tools': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                         'SLE-Module-Development-Tools/15-SP2/x86_64/product/',
            'dev-tools-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                'SLE-Module-Development-Tools/15-SP2/x86_64/update/',
        },
    }

    IMAGE_PATHS_DEVEL = {
        'ses7': {
            'ceph': 'registry.suse.de/devel/storage/7.0/containers/ses/7/ceph/ceph',
            'grafana': 'registry.suse.de/devel/storage/7.0/containers/ses/7/'
                       'ceph/grafana:latest',
            'prometheus': 'registry.suse.de/devel/storage/7.0/containers/ses/7/'
                          'ceph/prometheus-server:latest',
            'alertmanager': 'registry.suse.de/devel/storage/7.0/containers/ses/7/'
                            'ceph/prometheus-alertmanager:latest',
            'node-exporter': 'registry.suse.de/devel/storage/7.0/containers/ses/7/'
                             'ceph/prometheus-node-exporter:latest',
        },
        'ses7p': {
            'ceph': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/ceph/ceph',
            'grafana': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/'
                       'ceph/grafana:latest',
            'prometheus': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/'
                          'ceph/prometheus-server:latest',
            'alertmanager': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/'
                            'ceph/prometheus-alertmanager:latest',
            'node-exporter': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/'
                             'ceph/prometheus-node-exporter:latest',
            'haproxy': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/'
                       'ceph/haproxy:latest',
            'keepalived': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/ceph/'
                          'keepalived:latest',
            'snmp-gateway': 'registry.suse.de/devel/storage/7.0/pacific/containers/ses/7.1/ceph/'
                            'prometheus-snmp_notifier:latest',
        },
        'octopus': {
            'ceph': 'registry.opensuse.org/filesystems/ceph/octopus/images/ceph/ceph',
            'grafana': 'registry.opensuse.org/filesystems/ceph/octopus/images/'
                       'ceph/grafana:latest',
            'prometheus': 'registry.opensuse.org/filesystems/ceph/octopus/images/'
                          'ceph/prometheus-server:latest',
            'alertmanager': 'registry.opensuse.org/filesystems/ceph/octopus/images/'
                            'ceph/prometheus-alertmanager:latest',
            'node-exporter': 'registry.opensuse.org/filesystems/ceph/octopus/images/'
                             'ceph/prometheus-node-exporter:latest',
        },
        'pacific': {
            'ceph': 'registry.opensuse.org/filesystems/ceph/pacific/images/ceph/ceph',
            'grafana': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                       'ceph/grafana:latest',
            'prometheus': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                          'ceph/prometheus-server:latest',
            'alertmanager': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                            'ceph/prometheus-alertmanager:latest',
            'node-exporter': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                             'ceph/prometheus-node-exporter:latest',
            'haproxy': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                       'ceph/haproxy:latest',
            'keepalived': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                          'ceph/keepalived:latest',
            'snmp-gateway': 'registry.opensuse.org/filesystems/ceph/pacific/images/'
                            'ceph/prometheus-snmp_notifier:latest',
        },
    }

    IMAGE_PATHS_PRODUCT = {
        'ses7': {
            'ceph': 'registry.suse.com/ses/7/ceph/ceph',
        },
        'ses7p': {
            'ceph': 'registry.suse.com/ses/7.1/ceph/ceph',
        }
    }

    INTERNAL_MEDIA_REPOS = {
        'ses6': {
            'ses6-internal-media': 'http://download.suse.de/ibs/Devel:/Storage:/6.0/images/repo/'
                                   'SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Media/',
        },
        'ses7': {
            'ses7-internal-media': 'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
                                   'SUSE-Enterprise-Storage-7-POOL-Internal-x86_64-Media/',
        },
        'ses7p': {
            'ses7-internal-media': (
                'http://download.suse.de/ibs/Devel:/Storage:/7.0:/Pacific/images/repo/'
                'SUSE-Enterprise-Storage-7.1-POOL-Internal-x86_64-Media/'
            ),
        },
    }

    JINJA_ENV = Environment(loader=PackageLoader('seslib', 'templates'), trim_blocks=True)

    LOGFILE = None

    # A dict of string templates for repo urls. These templates are used to
    # generate the repo urls used during maintenance update testing
    MAINTENANCE_REPO_TEMPLATES = {
        'ses6': {
            '{}-update':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_SLE-15_Update',
            '{}-update-sp1':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_SLE-15-SP1_Update',
            '{}-storage':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_Updates_Storage_6_x86_64'
        },
        'ses7': {
            '{}-update':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_SLE-15_Update',
            '{}-update-sp2':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_SLE-15-SP2_Update',
            '{}-storage':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_Updates_Storage_7_x86_64'
        },
        'ses7p': {
            '{}-update':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_SLE-15_Update',
            '{}-update-sp3':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_SLE-15-SP3_Update',
            '{}-storage':
                'http://download.suse.de/ibs/SUSE:/Maintenance:/{}/SUSE_Updates_Storage_7.1_x86_64'
        }
    }

    MAKECHECK_DEFAULT_RAM = 8

    MAKECHECK_DEFAULT_REPO_BRANCH = {
        'sles-15-sp1': {
            'repo': 'https://github.com/SUSE/ceph',
            'branch': 'ses6-downstream-commits',
        },
        'sles-15-sp2': {
            'repo': 'https://github.com/SUSE/ceph',
            'branch': 'ses7',
        },
        'sles-15-sp3': {
            'repo': 'https://github.com/SUSE/ceph',
            'branch': 'ses7p',
        },
        'leap-15.1': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'nautilus',
        },
        'leap-15.2': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'octopus',
        },
        'leap-15.3': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'pacific',
        },
        'leap-15.4': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'main',
        },
        'tumbleweed': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'master',
        },
        'ubuntu-bionic': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'master',
        },
        'ubuntu-focal': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'main',
        },
    }

    METADATA_FILENAME = ".metadata"

    OPENSUSE_REPOS = {
        'leap-15.2': {
            'repo-oss': 'http://download.opensuse.org/distribution/leap/15.2/repo/oss/',
            'repo-update': 'http://download.opensuse.org/update/leap/15.2/oss/',
        },
        'leap-15.3': {
            'repo-oss': 'http://download.opensuse.org/distribution/leap/15.3/repo/oss/',
            'repo-update': 'http://download.opensuse.org/update/leap/15.3/oss/',
        },
    }

    OS_ALIASED_BOXES = {
        'opensuse/Leap-15.2.x86_64': 'leap-15.2',
        'opensuse/Leap-15.3.x86_64': 'leap-15.3',
        'opensuse/Tumbleweed.x86_64': 'tumbleweed',
        'generic/ubuntu1804': 'ubuntu-bionic',
        'generic/ubuntu2004': 'ubuntu-focal',
    }

    OS_BOX_ALIASES = {v: k for k, v in OS_ALIASED_BOXES.items()}

    OS_BOX_MAPPING = {
        'leap-15.1': 'https://download.opensuse.org/repositories/Virtualization:/'
                     'Appliances:/Images:/openSUSE-Leap-15.1/images/'
                     'Leap-15.1.x86_64-libvirt.box',
        'tumbleweed': 'https://download.opensuse.org/repositories/Virtualization:/'
                      'Appliances:/Images:/openSUSE-Tumbleweed/openSUSE_Tumbleweed/'
                      'Tumbleweed.x86_64-libvirt.box',
        'opensuse/Tumbleweed.x86_64': 'opensuse/Tumbleweed.x86_64',
        'sles-15-sp1': 'http://download.nue.suse.com/ibs/Virtualization:/Vagrant:/SLE-15-SP1/'
                       'images/SLES15-SP1-Vagrant.x86_64-libvirt.box',
        'leap-15.2': 'https://download.opensuse.org/repositories/Virtualization:/'
                     'Appliances:/Images:/openSUSE-Leap-15.2/images/'
                     'Leap-15.2.x86_64-libvirt.box',
        'opensuse/Leap-15.2.x86_64': 'opensuse/Leap-15.2.x86_64',
        'opensuse/Leap-15.3.x86_64': 'opensuse/Leap-15.3.x86_64',
        'sles-15-sp2': 'http://download.nue.suse.com/ibs/Virtualization:/Vagrant:/SLE-15-SP2/'
                       'images/SLES15-SP2-Vagrant.x86_64-libvirt.box',
        'sles-15-sp3': 'http://download.nue.suse.com/ibs/Virtualization:/Vagrant:/SLE-15-SP3/'
                       'images/SLES15-SP3-Vagrant.x86_64-libvirt.box',
        'sles-15-sp4': 'http://download.nue.suse.com/ibs/Virtualization:/Vagrant:/SLE-15-SP4/'
                       'images/SLES15-SP4-Vagrant.x86_64-libvirt.box',
        'sles-15-sp5': 'http://download.nue.suse.com/ibs/Virtualization:/Vagrant:/SLE-15-SP5/'
                       'images/SLES15-SP5-Vagrant.x86_64-libvirt.box',
        'generic/ubuntu1804': 'generic/ubuntu1804',
        'leap-15.4': 'https://download.opensuse.org/repositories/Virtualization:/'
                     'Appliances:/Images:/openSUSE-Leap-15.4/images/'
                     'Leap-15.4.x86_64-libvirt.box',
    }

    OS_MAKECHECK_REPOS = {
        'sles-15-sp1': {
            'desktop-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                            'SLE-Module-Desktop-Applications/15-SP1/x86_64/product/',
            'desktop-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                   'SLE-Module-Desktop-Applications/15-SP1/x86_64/update/',
            'dev-tools': 'http://dist.suse.de/ibs/SUSE/Products/'
                         'SLE-Module-Development-Tools/15-SP1/x86_64/product/',
            'dev-tools-update': 'http://dist.suse.de/ibs/SUSE/Products/'
                                'SLE-Module-Development-Tools/15-SP1/x86_64/product/',
            'workstation': 'http://download.nue.suse.com/ibs/SUSE:/SLE-15-SP1:/GA:/TEST/images/'
                           'repo/SLE-15-SP1-Product-WE-POOL-x86_64-Media1/',
            'workstation-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Product-WE/'
                                  '15-SP1/x86_64/update/',
        },
        'sles-15-sp2': {
            'desktop-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                            'SLE-Module-Desktop-Applications/15-SP2/x86_64/product/',
            'desktop-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                   'SLE-Module-Desktop-Applications/15-SP2/x86_64/update/',
            'dev-tools': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                         'SLE-Module-Development-Tools/15-SP2/x86_64/product/',
            'dev-tools-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                'SLE-Module-Development-Tools/15-SP2/x86_64/update/',
            'workstation': 'http://download.nue.suse.com/ibs/SUSE:/SLE-15-SP2:/GA:/TEST/images/'
                           'repo/SLE-15-SP2-Product-WE-POOL-x86_64-Media1/',
            'workstation-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Product-WE/'
                                  '15-SP2/x86_64/update/',
        },
        'sles-15-sp3': {
            'desktop-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                            'SLE-Module-Desktop-Applications/15-SP3/x86_64/product/',
            'desktop-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                   'SLE-Module-Desktop-Applications/15-SP3/x86_64/update/',
            'dev-tools': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                         'SLE-Module-Development-Tools/15-SP3/x86_64/product/',
            'dev-tools-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                'SLE-Module-Development-Tools/15-SP3/x86_64/update/',
            'workstation': 'http://download.nue.suse.com/ibs/SUSE:/SLE-15-SP3:/GA:/TEST/images/'
                           'repo/SLE-15-SP3-Product-WE-POOL-x86_64-Media1/',
            'workstation-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Product-WE/'
                                  '15-SP3/x86_64/update/',
        },
    }

    OS_PACKAGE_MANAGER_MAPPING = {
        'sles-15-sp1': 'zypper',
        'sles-15-sp2': 'zypper',
        'sles-15-sp3': 'zypper',
        'sles-15-sp4': 'zypper',
        'sles-15-sp5': 'zypper',
        'leap-15.1': 'zypper',
        'leap-15.2': 'zypper',
        'leap-15.3': 'zypper',
        'leap-15.4': 'zypper',
        'tumbleweed': 'zypper',
        'ubuntu-bionic': 'apt',
        'ubuntu-focal': 'apt',
    }

    OS_CA_REPO = {
        'sles-15-sp1': 'http://download.nue.suse.com/ibs/SUSE:/CA/SLE_15_SP1/SUSE:CA.repo',
        'sles-15-sp2': 'http://download.nue.suse.com/ibs/SUSE:/CA/SLE_15_SP2/SUSE:CA.repo',
        'sles-15-sp3': 'http://download.nue.suse.com/ibs/SUSE:/CA/SLE_15_SP3/SUSE:CA.repo',
        'sles-15-sp4': 'http://download.nue.suse.com/ibs/SUSE:/CA/SLE_15_SP4/SUSE:CA.repo',
        'sles-15-sp5': 'http://download.nue.suse.com/ibs/SUSE:/CA/SLE_15_SP5/SUSE:CA.repo',
    }

    OS_REPOS = {
        'sles-15-sp1': {
            'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP1/x86_64/'
                       'product/',
            'product-update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-Product-SLES/15-SP1/'
                              'x86_64/update/',
            'base': 'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP1/'
                    'x86_64/product/',
            'update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP1/'
                      'x86_64/update/',
            'server-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP1/x86_64/product/',
            'server-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP1/x86_64/update/',
            'storage': 'http://download.nue.suse.com/ibs/SUSE/Products/Storage/6/x86_64/product/',
            'storage-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/Storage/6/x86_64/'
                              'update/',
        },
        'sles-15-sp2': {
            'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP2/x86_64/'
                       'product/',
            'product-update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-Product-SLES/15-SP2/'
                              'x86_64/update/',
            'base': 'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP2/'
                    'x86_64/product/',
            'update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP2/'
                      'x86_64/update/',
            'server-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP2/x86_64/product/',
            'server-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP2/x86_64/update/',
            'storage': 'http://download.nue.suse.com/ibs/SUSE/Products/Storage/7/x86_64/product/',
            'storage-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/Storage/7/x86_64/'
                              'update/',
        },
        'sles-15-sp3': {
            'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP3/x86_64/'
                       'product/',
            'product-update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-Product-SLES/15-SP3/'
                              'x86_64/update/',
            'base': 'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP3/'
                    'x86_64/product/',
            'update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP3/'
                      'x86_64/update/',
            'server-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP3/x86_64/product/',
            'server-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP3/x86_64/update/',
            'storage': 'http://download.nue.suse.com/ibs/SUSE/Products/Storage/7.1/x86_64/product/',
            'storage-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/Storage/7.1/x86_64/'
                              'update/',
        },
        'sles-15-sp4': {
            'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP4/x86_64/'
                       'product/',
            'product-update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-Product-SLES/15-SP4/'
                              'x86_64/update/',
            'base': 'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP4/'
                    'x86_64/product/',
            'update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP4/'
                      'x86_64/update/',
            'server-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP4/x86_64/product/',
            'server-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP4/x86_64/update/',
        },
        'sles-15-sp5': {
            'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP5/x86_64/'
                       'product/',
            'product-update': 'http://dist.suse.de/ibs/SUSE/Updates/SLE-Product-SLES/15-SP5/'
                              'x86_64/update/',
            'base': 'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP5/'
                    'x86_64/product/',
            'update': 'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP5/'
                      'x86_64/update/',
            'server-apps': 'http://download.nue.suse.com/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP5/x86_64/product/',
            'server-apps-update': 'http://download.nue.suse.com/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP5/x86_64/update/',
        },
    }

    REASONABLE_TIMEOUT_IN_SECONDS = 3200

    ROLES_DEFAULT = {
        "caasp4": [["master"], ["worker"], ["worker"], ["loadbalancer"]],
        "k3s": [["master"], ["worker"], ["worker"], ["worker"], ["worker"]],
        "makecheck": [["makecheck"]],
        "nautilus": [["master", "client", "prometheus", "grafana"],
                     ["storage", "mon", "mgr", "rgw", "igw"],
                     ["storage", "mon", "mgr", "mds", "igw", "nfs"],
                     ["storage", "mon", "mgr", "mds", "rgw", "nfs"]],
        "octopus": [["admin", "master", "client", "prometheus", "grafana", "alertmanager",
                     "node-exporter"],
                    ["bootstrap", "storage", "mon", "mgr", "rgw", "igw", "node-exporter"],
                    ["storage", "mon", "mgr", "mds", "igw", "node-exporter"],
                    ["storage", "mon", "mgr", "mds", "rgw", "node-exporter"]],
        "ses7": [["admin", "master", "client", "prometheus", "grafana", "alertmanager",
                  "node-exporter"],
                 ["bootstrap", "storage", "mon", "mgr", "rgw", "igw", "node-exporter"],
                 ["storage", "mon", "mgr", "mds", "igw", "node-exporter"],
                 ["storage", "mon", "mgr", "mds", "rgw", "nfs", "node-exporter"]]
    }

    ROLES_DEFAULT_BY_VERSION = {
        'caasp4': ROLES_DEFAULT["caasp4"],
        'k3s': ROLES_DEFAULT["k3s"],
        'makecheck': ROLES_DEFAULT["makecheck"],
        'nautilus': ROLES_DEFAULT["nautilus"],
        'octopus': ROLES_DEFAULT["octopus"],
        'pacific': ROLES_DEFAULT["octopus"],
        'ses6': ROLES_DEFAULT["nautilus"],
        'ses7': ROLES_DEFAULT["ses7"],
        'ses7p': ROLES_DEFAULT["ses7"],
    }

    ROLES_KNOWN = [
        "admin",
        "alertmanager",
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
        "node-exporter",
        "prometheus",
        "rgw",
        "storage",
        "suma",
        "worker",
    ]

    ROLES_SINGLE_NODE = {
        "caasp4": "[ master ]",
        "k3s": "[ master ]",
        "nautilus": "[ master, storage, mon, mgr, prometheus, grafana, mds, igw, rgw, "
                    "nfs ]",
        "octopus": "[ master, admin, bootstrap, storage, mon, mgr, mds, igw, rgw, "
                   "prometheus, grafana, alertmanager, node-exporter ]",
        "ses7": "[ master, admin, bootstrap, storage, mon, mgr, mds, igw, rgw, "
                   "prometheus, grafana, alertmanager, node-exporter ]",
    }

    SSH_KEY_NAME = 'sesdev'  # do NOT use 'id_rsa'

    VAGRANT_DEBUG = None

    VERBOSE = None

    VERSION_DEVEL_REPOS = {
        'ses6': {
            'sles-15-sp1': [
                'http://download.nue.suse.com/ibs/Devel:/Storage:/6.0/images/repo/'
                'SUSE-Enterprise-Storage-6-POOL-x86_64-Media1/'
            ],
        },
        'nautilus': {
            'leap-15.1': [
                'https://download.opensuse.org/repositories/filesystems:/ceph:/nautilus/'
                'openSUSE_Leap_15.1/'
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
            'ubuntu-bionic': [],
            'ubuntu-focal': [],
        },
        'pacific': {
            'leap-15.2': [
                'https://download.opensuse.org/repositories/filesystems:/ceph:/pacific/'
                'openSUSE_Leap_15.2'
            ],
            'leap-15.3': [
                'https://download.opensuse.org/repositories/filesystems:/ceph:/pacific/'
                'openSUSE_Leap_15.3'
            ],
            'tumbleweed': [
                'https://download.opensuse.org/repositories/filesystems:/ceph:/pacific/'
                'openSUSE_Tumbleweed'
            ],
            'ubuntu-focal': [],
        },
        'ses7': {
            'sles-15-sp2': [
                'http://download.nue.suse.com/ibs/Devel:/Storage:/7.0/images/repo/'
                'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
            ],
        },
        'ses7p': {
            'sles-15-sp3': [
                'http://download.nue.suse.com/ibs/Devel:/Storage:/7.0:/Pacific/images/repo/'
                'SUSE-Enterprise-Storage-7.1-POOL-x86_64-Media1/'
            ],
        },
        'caasp4': {
            'sles-15-sp2': [
                'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Containers/15-SP2/'
                'x86_64/product/',
                'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Containers/15-SP2/x86_64/'
                'update/',
                'http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Public-Cloud/15-SP2/'
                'x86_64/product/',
                'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Public-Cloud/15-SP2/'
                'x86_64/update/',
                'http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Public-Cloud/15-SP1/'
                'x86_64/update/',
                'http://download.nue.suse.com/ibs/SUSE:/SLE-15-SP2:/Update:/Products:/CaaSP:/4.5/'
                'standard/',
                'http://download.nue.suse.com/ibs/SUSE/Updates/SUSE-CAASP/4.5/x86_64/update/'
            ],
        },
        'k3s': {
            'sles-15-sp3': [],
            'sles-15-sp4': [],
            'sles-15-sp5': [],
            'tumbleweed': [],
        },
        'makecheck': {
            'sles-15-sp1': [
                'http://download.nue.suse.com/ibs/Devel:/Storage:/6.0/images/repo/'
                'SUSE-Enterprise-Storage-6-POOL-x86_64-Media1/',
                # '10000!http://download.nue.suse.com/ibs/Devel:/Storage:/6.0/images/repo/'
                # 'SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Media/',
            ],
            'leap-15.1': [],
            'sles-15-sp2': [
                'http://download.nue.suse.com/ibs/Devel:/Storage:/7.0/images/repo/'
                'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/',
                '10000!http://download.nue.suse.com/ibs/Devel:/Storage:/7.0/images/repo/'
                'SUSE-Enterprise-Storage-7-POOL-Internal-x86_64-Media/',
            ],
            'sles-15-sp3': [
                'http://download.nue.suse.com/ibs/Devel:/Storage:/7.0:/Pacific/images/repo/'
                'SUSE-Enterprise-Storage-7.1-POOL-x86_64-Media1/',
                '10000!http://download.nue.suse.com/ibs/Devel:/Storage:/7.0:/Pacific/images/repo/'
                'SUSE-Enterprise-Storage-7.1-POOL-Internal-x86_64-Media/',
            ],
            'leap-15.2': [],
            'leap-15.3': [],
            'leap-15.4': [],
            'tumbleweed': [],
        },
    }

    VERSION_PREFERRED_DEPLOYMENT_TOOL = {
        'ses6': 'deepsea',
        'ses7': 'cephadm',
        'ses7p': 'cephadm',
        'nautilus': 'deepsea',
        'octopus': 'cephadm',
        'pacific': 'cephadm',
        'caasp4': None,
        'k3s': None,
        'makecheck': None,
    }

    VERSION_PREFERRED_OS = {
        'ses6': 'sles-15-sp1',
        'ses7': 'sles-15-sp2',
        'ses7p': 'sles-15-sp3',
        'nautilus': 'leap-15.1',
        'octopus': 'leap-15.2',
        'pacific': 'leap-15.3',
        'caasp4': 'sles-15-sp2',
        'k3s': 'tumbleweed',
        'makecheck': 'tumbleweed',
    }

    # Human readable names corresponding to official products where applicable
    VERSION_OFFICIAL = {
        'ses5': 'SES 5',
        'nautilus': 'Ceph Nautilus',
        'ses6': 'SES 6',
        'octopus': 'Ceph Octopus',
        'ses7': 'SES 7',
        'pacific': 'Ceph Pacific',
        'ses7p': 'SES 7.1',
        'makecheck': 'Ceph makecheck',
    }

    ZYPPER_PRIO_ELEVATED = 50

    @classmethod
    def init_path_to_qa(cls, full_path_to_sesdev_executable):
        if full_path_to_sesdev_executable.startswith('/usr'):
            cls.PATH_TO_QA = '/usr/share/sesdev/qa'
        else:
            cls.PATH_TO_QA = os.path.join(
                os.path.dirname(full_path_to_sesdev_executable),
                '../qa/'
            )
