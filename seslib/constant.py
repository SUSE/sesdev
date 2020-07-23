import os

from pathlib import Path
from jinja2 import Environment, PackageLoader


class Constant():

    A_WORKING_DIR = os.path.join(Path.home(), '.sesdev')

    CEPH_SALT_REPO = 'https://github.com/ceph/ceph-salt'

    CEPH_SALT_BRANCH = 'master'

    CONFIG_FILE = os.path.join(A_WORKING_DIR, 'config.yaml')

    CORE_VERSIONS = ['ses5', 'nautilus', 'ses6', 'octopus', 'ses7', 'pacific']

    DEBUG = False

    DEFAULT_ROLES = {
        "caasp4": [["master"], ["worker"], ["worker"], ["loadbalancer"]],
        "luminous": [["master", "client", "openattic"],
                     ["storage", "mon", "mgr", "rgw", "igw"],
                     ["storage", "mon", "mgr", "mds", "nfs"],
                     ["storage", "mon", "mgr", "mds", "rgw", "nfs"]],
        "makecheck": [["makecheck"]],
        "nautilus": [["master", "client", "prometheus", "grafana"],
                     ["storage", "mon", "mgr", "rgw", "igw"],
                     ["storage", "mon", "mgr", "mds", "igw", "nfs"],
                     ["storage", "mon", "mgr", "mds", "rgw", "nfs"]],
        "octopus": [["master", "client", "prometheus", "grafana"],
                    ["bootstrap", "storage", "mon", "mgr", "rgw", "igw"],
                    ["storage", "mon", "mgr", "mds", "igw", "nfs"],
                    ["storage", "mon", "mgr", "mds", "rgw", "nfs"]]
    }

    IMAGE_PATHS = {
        'ses7': 'registry.suse.de/devel/storage/7.0/containers/ses/7/ceph/ceph',
        'octopus': 'registry.opensuse.org/filesystems/ceph/octopus/images/ceph/ceph',
        'pacific': 'registry.opensuse.org/filesystems/ceph/master/upstream/images/ceph/ceph',
    }

    JINJA_ENV = Environment(loader=PackageLoader('seslib', 'templates'), trim_blocks=True)

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

    LOGFILE = None

    MAKECHECK_DEFAULT_RAM = 8

    MAKECHECK_DEFAULT_REPO_BRANCH = {
        'sles-12-sp3': {
            'repo': 'https://github.com/SUSE/ceph',
            'branch': 'ses5',
        },
        'sles-15-sp1': {
            'repo': 'https://github.com/SUSE/ceph',
            'branch': 'ses6-downstream-commits',
        },
        'leap-15.1': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'nautilus',
        },
        'sles-15-sp2': {
            'repo': 'https://github.com/SUSE/ceph',
            'branch': 'ses7',
        },
        'leap-15.2': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'octopus',
        },
        'tumbleweed': {
            'repo': 'https://github.com/ceph/ceph',
            'branch': 'master',
        },
    }

    METADATA_FILENAME = ".metadata"

    OS_BOX_MAPPING = {
        'leap-15.1': 'https://download.opensuse.org/repositories/Virtualization:/'
                     'Appliances:/Images:/openSUSE-Leap-15.1/images/'
                     'Leap-15.1.x86_64-libvirt.box',
        'tumbleweed': 'https://download.opensuse.org/repositories/Virtualization:/'
                      'Appliances:/Images:/openSUSE-Tumbleweed/openSUSE_Tumbleweed/'
                      'Tumbleweed.x86_64-libvirt.box',
        'sles-15-sp1': 'http://download.suse.de/ibs/Virtualization:/Vagrant:/SLE-15-SP1/images/'
                       'SLES15-SP1-Vagrant.x86_64-libvirt.box',
        'sles-12-sp3': 'http://download.suse.de/ibs/Devel:/Storage:/5.0/vagrant/'
                       'sle12sp3.x86_64.box',
        'leap-15.2': 'https://download.opensuse.org/repositories/Virtualization:/'
                     'Appliances:/Images:/openSUSE-Leap-15.2/images/'
                     'Leap-15.2.x86_64-libvirt.box',
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
            'product': 'http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP1/x86_64/'
                       'product/',
            'base': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP1/'
                    'x86_64/product/',
            'update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP1/'
                      'x86_64/update/',
            'server-apps': 'http://download.suse.de/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP1/x86_64/product/',
            'server-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP1/x86_64/update/',
            'desktop-apps': 'http://download.suse.de/ibs/SUSE/Products/'
                            'SLE-Module-Desktop-Applications/15-SP1/x86_64/product/',
            'desktop-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                                   'SLE-Module-Desktop-Applications/15-SP1/x86_64/update/',
            'dev-tools': 'http://dist.suse.de/ibs/SUSE/Products/'
                         'SLE-Module-Development-Tools/15-SP1/x86_64/product/',
            'dev-tools-update': 'http://dist.suse.de/ibs/SUSE/Products/'
                                'SLE-Module-Development-Tools/15-SP1/x86_64/product/',
            'workstation': 'http://download.suse.de/ibs/SUSE:/SLE-15-SP1:/GA:/TEST/images/repo/'
                           'SLE-15-SP1-Product-WE-POOL-x86_64-Media1/',
            'workstation-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Product-WE/15-SP1/'
                                  'x86_64/update/',
            'storage': 'http://download.suse.de/ibs/SUSE/Products/Storage/6/x86_64/product/',
            'storage-update': 'http://download.suse.de/ibs/SUSE/Updates/Storage/6/x86_64/update/'
        },
        'sles-15-sp2': {
            'base': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP2/'
                    'x86_64/product/',
            'update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP2/'
                      'x86_64/update/',
            'server-apps': 'http://download.suse.de/ibs/SUSE/Products/'
                           'SLE-Module-Server-Applications/15-SP2/x86_64/product/',
            'server-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                                  'SLE-Module-Server-Applications/15-SP2/x86_64/update/',
            'desktop-apps': 'http://download.suse.de/ibs/SUSE/Products/'
                            'SLE-Module-Desktop-Applications/15-SP2/x86_64/product/',
            'desktop-apps-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                                   'SLE-Module-Desktop-Applications/15-SP2/x86_64/update/',
            'dev-tools': 'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Development-Tools/'
                         '15-SP2/x86_64/product/',
            'dev-tools-update': 'http://download.suse.de/ibs/SUSE/Updates/'
                                'SLE-Module-Development-Tools/15-SP2/x86_64/update/',
            'workstation': 'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/GA:/TEST/images/repo/'
                           'SLE-15-SP2-Product-WE-POOL-x86_64-Media1/',
            'workstation-update': 'http://download.suse.de/ibs/SUSE/Updates/SLE-Product-WE/15-SP2/'
                                  'x86_64/update/',
            'storage7-media': 'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/Update:/Products:/'
                              'SES7/images/repo/SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/',
        },
    }

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

    VAGRANT_DEBUG = None

    VERBOSE = None

    VERSION_DEFAULT_ROLES = {
        'caasp4': DEFAULT_ROLES["caasp4"],
        'makecheck': DEFAULT_ROLES["makecheck"],
        'nautilus': DEFAULT_ROLES["nautilus"],
        'octopus': DEFAULT_ROLES["octopus"],
        'pacific': DEFAULT_ROLES["octopus"],
        'ses5': DEFAULT_ROLES["luminous"],
        'ses6': DEFAULT_ROLES["nautilus"],
        'ses7': DEFAULT_ROLES["octopus"],
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
                'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
                'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
            ],
        },
        'caasp4': {
            'sles-15-sp1': [
                'http://download.suse.de/ibs/SUSE:/SLE-15-SP1:/Update:/Products:/CASP40:/Update/'
                'standard/',
                'http://download.suse.de/ibs/SUSE:/SLE-15-SP1:/Update:/Products:/CASP40/standard/',
                'http://download.suse.de/ibs/SUSE/Products/SLE-Module-Containers/15-SP1/x86_64/'
                'product/'
            ],
        },
        'makecheck': {
            'sles-12-sp3': [
                'http://download.suse.de/ibs/Devel:/Storage:/5.0/images/repo/'
                'SUSE-Enterprise-Storage-5-POOL-x86_64-Media1/',
                '10000!http://download.suse.de/ibs/Devel:/Storage:/5.0/images/repo/'
                'SUSE-Enterprise-Storage-5-POOL-Internal-x86_64-Media/',
            ],
            'sles-15-sp1': [
                'http://download.suse.de/ibs/Devel:/Storage:/6.0/images/repo/'
                'SUSE-Enterprise-Storage-6-POOL-x86_64-Media1/',
                # '10000!http://download.suse.de/ibs/Devel:/Storage:/6.0/images/repo/'
                # 'SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Media/',
            ],
            'leap-15.1': [],
            'sles-15-sp2': [
                'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
                'SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/',
                '10000!http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/'
                'SUSE-Enterprise-Storage-7-POOL-Internal-x86_64-Media/',
            ],
            'leap-15.2': [],
            'tumbleweed': [],
        },
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
