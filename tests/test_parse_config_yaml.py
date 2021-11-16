from seslib.settings import Settings
from seslib.constant import Constant


from unittest.mock import patch, mock_open
from tempfile import mktemp


def test_parse_config_yaml__return_empty_dict():
    Constant.CONFIG_FILE = mktemp()
    config_tree = Settings._load_config_file()
    assert config_tree == {}, 'reading non-existent file does not return empty dict'


# Examples from the documentation of how config.yaml can be used.
# Excluding the ability to use references in YAML, that is not from the docs but made up.
config_yaml = '''
libvirt_use_ssh: true
libvirt_user: root
libvirt_private_key_file: $HOME/.ssh/id_rsa
libvirt_host: foo
version_devel_repos:
  octopus:
      leap-15.2:
          - 'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/openSUSE_Leap_15.2'
image_paths_devel:
    octopus: 'registry.opensuse.org/filesystems/ceph/octopus/images/ceph/ceph'
container_registry:
    prefix: 'registry.suse.de'
    location: '1.2.3.4:5000'
    insecure: True
version_default_roles: &default
    octopus:
        - [master, mon, mgr, storage]
        - [mon, mgr, storage]
        - [mon, mgr, storage]
other_roles: *default
    '''  # noqa


@patch('os.path.exists', return_value=True)
@patch('os.path.isfile', return_value=True)
@patch('builtins.open', mock_open(read_data=config_yaml))
def test_parse_config_yaml(isfile, exists):
    settings = Settings._load_config_file()
    assert settings['libvirt_host'] == 'foo'
    assert settings['other_roles']['octopus'] == [
        ['master', 'mon', 'mgr', 'storage'],
        ['mon', 'mgr', 'storage'],
        ['mon', 'mgr', 'storage'],
    ]
    assert len(settings['other_roles'].keys()) == 9
