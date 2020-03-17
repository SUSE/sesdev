# sesdev - deploy and manage SES/Ceph clusters<br/> [![Travis Build Status](https://travis-ci.org/SUSE/sesdev.svg?branch=master)](https://travis-ci.org/SUSE/sesdev) [![Jenkins Build Status](https://ceph-ci.suse.de/job/sesdev-integration/job/master/badge/icon)](https://ceph-ci.suse.de/job/sesdev-integration/job/master/)

`sesdev` is a CLI tool to deploy Ceph clusters (both the upstream and SUSE
downstream versions).

This tool uses [Vagrant](https://www.vagrantup.com/) behind the scenes to create
the VMs and run the deployment scripts.

## Table of Contents

[//]: # (To generate a new TOC, first install https://github.com/ekalinin/github-markdown-toc)
[//]: # (and then run "gh-md-toc README.md")
[//]: # (the new TOC will appear on stdout: the expectation is that the maintainer will do the rest.)

* [Installation](#installation)
   * [Install sesdev on openSUSE](#install-sesdev-on-opensuse)
      * [Install KVM/QEMU and Libvirt](#install-kvmqemu-and-libvirt)
      * [Add user to libvirt group](#add-user-to-libvirt-group)
      * [Install Vagrant](#install-vagrant)
      * [Install sesdev from package](#install-sesdev-from-package)
   * [Install sesdev on Fedora Linux](#install-sesdev-on-fedora-linux)
      * [Install KVM/QEMU and Libvirt](#install-kvmqemu-and-libvirt-1)
      * [Install sesdev from package](#install-sesdev-from-package-1)
   * [Install sesdev on Debian/Ubuntu](#install-sesdev-on-debianubuntu)
   * [Install sesdev from source](#install-sesdev-from-source)
      * [Running the unit tests](#running-the-unit-tests)
* [Usage](#usage)
   * [Create/deploy a cluster](#createdeploy-a-cluster)
      * [Custom zypper repo (to be added together with the default repos)](#custom-zypper-repo-to-be-added-together-with-the-default-repos)
      * [Custom zypper repos (completely replace the default repos)](#custom-zypper-repos-completely-replace-the-default-repos)
      * [Custom image paths](#custom-image-paths)
      * [Custom default roles](#custom-default-roles)
      * [config.yaml examples](#configyaml-examples)
         * [octopus from filesystems:ceph:octopus](#octopus-from-filesystemscephoctopus)
         * [octopus from filesystems:ceph:master:upstream](#octopus-from-filesystemscephmasterupstream)
         * [ses7 from Devel:Storage:7.0](#ses7-from-develstorage70)
         * [ses7 from Devel:Storage:7.0:CR](#ses7-from-develstorage70cr)
   * [List existing deployments](#list-existing-deployments)
   * [SSH access to a cluster](#ssh-access-to-a-cluster)
   * [Copy files into and out of a cluster](#copy-files-into-and-out-of-a-cluster)
   * [Services port-forwarding](#services-port-forwarding)
   * [Temporarily stop a cluster](#temporarily-stop-a-cluster)
   * [Destroy a cluster](#destroy-a-cluster)
* [Common pitfalls](#common-pitfalls)
   * [Domain about to create is already taken](#domain-about-to-create-is-already-taken)
   * [Storage pool not found: no storage pool with matching name 'default'](#storage-pool-not-found-no-storage-pool-with-matching-name-default)
   * [When sesdev deployments get destroyed, virtual networks get left behind](#when-sesdev-deployments-get-destroyed-virtual-networks-get-left-behind)
* [Contributing](#contributing)


## Installation

First, you should have both [QEMU](https://www.qemu.org/) and
[Libvirt](https://libvirt.org/) installed in some machine to host the VMs
created by sesdev (using Vagrant behind the scenes).

Installable packages for various Linux distributions like Fedora or openSUSE can
be found on the [openSUSE Build Service](https://software.opensuse.org//download.html?project=filesystems%3Aceph&package=sesdev)
(OBS).

### Install sesdev on openSUSE

#### Install KVM/QEMU and Libvirt

```
$ sudo zypper -n install patterns-openSUSE-kvm_server \
patterns-server-kvm_tools bridge-utils
$ sudo systemctl enable libvirtd
$ sudo systemctl restart libvirtd
```

#### Add user to libvirt group

If you are running libvirt on the same machine where you installed sesdev, add
your user to the "libvirt" group to avoid "no polkit agent available" errors
when vagrant attempts to connect to the libvirt daemon:

```
$ sudo groupadd libvirt
groupadd: group 'libvirt' already exists
$ sudo usermod -a -G libvirt $USER
```

Log out, and then log back in. You should now be a member of the "libvirt"
group.

#### Install Vagrant

sesdev needs Vagrant to work.

```
$ sudo zypper ar https://download.opensuse.org/repositories/Virtualization:/vagrant/<repo> vagrant_repo
$ sudo zypper ref
$ sudo zypper -n install vagrant vagrant-libvirt
```

Where `<repo>` can be any of the openSUSE build targets currently enabled for
the [Virtualization:vagrant/vagrant package in the openSUSE Build Service](https://build.opensuse.org/package/show/Virtualization:vagrant/vagrant).

#### Install sesdev from package

sesdev itself can be installed either from package or from source. If you
prefer to install from package, follow the instructions in this section. If you
prefer to install from source, skip down to the "Install sesdev from source"
section.

```
$ sudo zypper ar https://download.opensuse.org/repositories/filesystems:/ceph/<repo> filesystems_ceph
$ sudo zypper ref
$ sudo zypper install sesdev
```

Where `<repo>` can be any of the openSUSE build targets currently enabled for
the [sesdev package in the openSUSE Build Service](https://build.opensuse.org/package/show/filesystems:ceph/sesdev).

At this point, sesdev should be installed and ready to use: refer to the "Usage"
chapter, below, for further information.

### Install sesdev on Fedora Linux

#### Install KVM/QEMU and Libvirt

```
$ sudo dnf install qemu-common qemu-kvm libvirt-daemon-kvm \
libvirt-daemon libvirt-daemon-driver-qemu vagrant-libvirt
$ sudo systemctl enable libvirtd
$ sudo systemctl restart libvirtd
```

#### Install sesdev from package

```
$ sudo dnf config-manager --add-repo \
https://download.opensuse.org/repositories/filesystems:/ceph/<distro>/filesystems:ceph.repo
dnf install sesdev
```

Where `<distro>` can be any of the Fedora build targets currently enabled for
the [sesdev package in the openSUSE Build Service](https://build.opensuse.org/package/show/filesystems:ceph/sesdev).

At this point, sesdev should be installed and ready to use: refer to the "Usage"
chapter, below, for further information.

### Install sesdev on Debian/Ubuntu

sesdev is known to work on recent Ubuntus, but there is no package for it: you
have to install from source. Follow the instructions given in
[Install sesdev from source](#install-sesdev-from-source) with the following
changes:

* use `apt install` instead of `zypper install`
* install `libvirt-dev` invstead of `libvirt-devel`

### Install sesdev from source

sesdev itself can be installed either from package or from source. If you
prefer to install from source, follow the instructions in this section. If you
prefer to install from package, scroll up to the "Install sesdev from package"
section for your operating system.

sesdev uses the libvirt API Python bindings, and these cannot be installed via
pip unless the RPM packages "gcc", "python3-devel", and "libvirt-devel" are
installed, first. Also, in order to clone the sesdev git repo, the "git-core"
package is needed. So, before proceeding, make sure that all of these packages
are installed in the system:

```
$ sudo zypper -n install gcc git-core libvirt-devel python3-devel
```

Now you can proceed to clone the sesdev source code repo, create and activate
a virtualenv, and install sesdev's Python dependencies in it:

```
$ git clone https://github.com/SUSE/sesdev.git
$ cd sesdev
$ virtualenv venv
$ source venv/bin/activate
$ pip install --editable .
```

Remember to re-run `pip install --editable .` after each git pull.

At this point, sesdev should be installed and ready to use: refer to the "Usage"
chapter, below, for further information.

#### Running the unit tests

If you are preparing a code change for submission and would like to run the
unit tests on it, make sure you have installed sesdev from source, as described
above, and the virtualenv is active. Then, follow the instructions below.

First, install the "tox" package in your system:

```
zypper -n install python3-tox
```

Then, execute the following commands in the top-level of your local git clone
to install the dependencies, including test dependencies:

```
pip install --editable ./[dev]
```

Finally, inspect the list of testing environments in `tox.ini` and choose one or
more that you are interested in. Here is an example, but the actual output might
be different:

```
$ tox --listenvs
py36
py37
lint
```

(This means you have three testing environments to choose from: `py36`, `py37`,
and `lint`.)

Finally, run your chosen test environment(s):

```
tox -e py36
tox -e lint
```

If you don't know which testing environment to choose, the command `tox` will
run *all* the testing environments.

CAVEAT: environments like `py36` and `py37` will only run if that exact version
of Python is installed on your system. So, if you've got Python 3.6 and you
want to run all possible tests:

```
tox -e py36,lint
```

## Usage

Run `sesdev --help` or `sesdev <command> --help` to get the available
options and description of the commands.

### Create/deploy a cluster

To create a single node Ceph cluster based on nautilus/leap-15.1 on your local
system, run the following command:

```
$ sesdev create nautilus --single-node mini
```

The `mini` argument is the ID of the deployment. You can create many deployments
by giving them different IDs.

If you would like to start the cluster VMs on a remote server via libvirt/SSH,
create a configuration file `$HOME/.sesdev/config.yaml` with the following
content:

```
libvirt_use_ssh: true
libvirt_user: <ssh_user>
libvirt_private_key_file: <private_key_file>   # defaults to $HOME/.ssh/id_rsa
libvirt_host: <hostname|ip address>
```

Note that passwordless SSH access to this user@host combination needs to be
configured and enabled.

To create a multi-node Ceph cluster, you can specify the nodes and their roles
using the `--roles` option.

The roles of each node are grouped in square brackets, separated by commas. The
nodes are separated by commas, too.

The following roles can be assigned:

* `master` - The master node, running management components like the Salt master
* `client` - Various Ceph client utilities
* `ganesha` - NFS Ganesha service
* `grafana` - Grafana metrics visualization (requires Prometheus)
* `igw` - iSCSI target gateway
* `mds` - CephFS MDS
* `mgr` - Ceph Manager instance
* `mon` - Ceph Monitor instance
* `prometheus` - Prometheus monitoring
* `rgw` - Ceph Object Gateway
* `storage` - OSD storage daemon
* `suma` - SUSE Manager (octopus only)

The following example will generate a cluster with four nodes: the master (Salt
Master) node that is also running a MON daemon, two storage (OSD) nodes that
will also run a MON, a MGR and an MDS, and another node that will run an iSCSI
gateway, an NFS-Ganesha gateway, and an RGW gateway.

```
$ sesdev create nautilus --roles="[master, mon], [storage, mon, mgr, mds], \
  [storage, mon, mgr, mds], [igw, ganesha, rgw]" big_cluster
```

CAVEAT: sesdev applies the "admin" role to all nodes, regardless of whether or
not the user specified it explicitly on the command line or in `config.yaml`.

#### Custom zypper repo (to be added together with the default repos)

Each deployment version (e.g. "octopus", "nautilus") is associated with
a set of zypper repos which are added on each VM that is created.

There are times when you may need to add additional zypper repo(s)
to all the VMs prior to deployment. In such a case, add one or more `--repo`
options to the command line, e.g.:

```
$ sesdev create nautilus --single-node --repo [URL_OF_REPO] mini
```

By default, the custom repo(s) will be added with an elevated priority,
to ensure that packages from these repos will be installed even if higher
RPM versions of those packages exist. If this behavior is not desired,
add `--no-repo-priority` to disable it.

#### Custom zypper repos (completely replace the default repos)

If the default zypper repos that are added to each VM
prior to deployment are completely wrong for your use case, you can override
them via `~/.sesdev/config.yaml`.

To do this, you have to be familiar with two of sesdev's internal dictionaries:
`OS_REPOS` and `VERSION_OS_REPO_MAPPING`. The former specifies repos that are
added to all VMs with a given operating system, regardless of the Ceph version
being deployed, and the latter specifies additional repos that are added to VMs
depending on the Ceph version being deployed. Refer to `seslib/__init__.py` for
the current defaults.

To override `OS_REPOS`, add an `os_repos:` stanza to your `~/.sesdev/config.yaml`.

To override `VERSION_OS_REPO_MAPPING`, add a `version_os_repo_mapping:` stanza to your `~/.sesdev/config.yaml`.

Please note that you need not copy-paste any parts of these internal
dictionaries from the source code into your config. You can selectively override
only those parts that you need. For example, the following config snippet will
override the default additional repos for "octopus" deployments on "leap-15.2",
but it will not change the defaults for any of the other deployment versions:

```
version_os_repo_mapping:
    octopus:
        leap-15.2:
            - 'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/openSUSE_Leap_15.2'
```

If you need a higher priority on one or more of the repos,
`version_os_repo_mapping` supports a "magic priority prefix" on the repo URL,
like so:

```
version_os_repo_mapping:
    octopus:
        leap-15.2:
            - '96!https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/openSUSE_Leap_15.2'
```

This would cause the zypper repo to be added at priority 96.


#### Custom image paths

In Ceph versions "octopus" and newer, the Ceph daemons run inside containers.
When the cluster is bootstrapped, a container image is downloaded from a remote
registry. The default image paths are set by the internal dictionary
`IMAGE_PATHS` in `seslib/__init__.py`. You can specify a different image path
using the `--image-path` option to, e.g., `sesdev create octopus`.

If you would like to permanently specify a different image path for one or more
Ceph versions, you can override the defaults by adding a stanza like the
following to your `~/.sesdev/config.yaml`:

```
image_paths:
    octopus: 'registry.opensuse.org/filesystems/ceph/octopus/images/ceph/ceph'
```

#### Custom default roles

When the user does not give the `--roles` option on the command line, `sesdev`
will use the default roles for the given deployment version. These defaults can
be changed by adding a `version_default_roles` stanza to your `~/.sesdev/config.yaml`:


```
version_default_roles:
    octopus:
        - [master, mon, mgr, storage]
        - [mon, mgr, storage]
        - [mon, mgr, storage]
```

#### config.yaml examples

##### octopus from filesystems:ceph:octopus

config.yaml:

```
version_os_repo_mapping:
    octopus:
        leap-15.2:
            - 'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/openSUSE_Leap_15.2'
image_paths:
    octopus: 'registry.opensuse.org/filesystems/ceph/octopus/images/ceph/ceph'
```

sesdev command line:

```
sesdev create octopus \
    --ceph-salt-repo https://github.com/ceph/ceph-salt.git \
    --ceph-salt-branch master \
    --qa-test \
    --single-node \
    octopus
```

##### octopus from filesystems:ceph:master:upstream

No config.yaml changes are needed, because this is the default configuration.

sesdev command is the same as for `filesystems:ceph:octopus`.

##### ses7 from Devel:Storage:7.0

This is the default, so no tweaking of config.yaml is necessary. Just:

```
sesdev create ses7 \
    --ceph-salt-repo https://github.com/ceph/ceph-salt.git \
    --ceph-salt-branch master \
    --qa-test \
    --single-node \
    ses7
```

Note that this will work even if there is no ceph package visible at
https://build.suse.de/project/show/Devel:Storage:7.0 since it uses the
installation media repo, not the "SLE_15_SP2" repo.

##### ses7 from Devel:Storage:7.0:CR

Since `Devel:Storage:7.0:CR/ceph` has the same version as
`filesystems:ceph:master:upstream/ceph`, this is an unadulterated upstream
build which requires special zypper priority to get it to install correctly in
SLE-15-SP2.

config.yaml:

```
version_os_repo_mapping:
    ses7:
        sles-15-sp2
            - 'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/Update:/Products:/SES7/images/repo/SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
            - 'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
            - '96!http://download.suse.de/ibs/Devel:/Storage:/7.0:/CR/SLE_15_SP2/'
image_paths:
    ses7: 'registry.suse.de/devel/storage/7.0/cr/containers/ses/7/ceph/ceph'
```

Thanks to the `config.yaml` shown above, the sesdev command line is the same as
in [ses7 from Devel:Storage:7.0](#ses7-from-develstorage70).

### List existing deployments

```
$ sesdev list
```

### SSH access to a cluster

```
$ sesdev ssh <deployment_id> [NODE]
```

Spawns an SSH shell to the master node, or to node `NODE` if explicitly
specified. You can check the existing node names with the following command:

```
$ sesdev show <deployment_id>
```

### Copy files into and out of a cluster

`sesdev` provides a subset of `scp` functionality. For details, see:

```
$ sesdev scp --help
```

### Services port-forwarding

It's possible to use an SSH tunnel to enble TCP port-forwarding for a service
running in the cluster. Currently, the following services can be forwarded:

* dashboard - The Ceph Dashboard (nautilus and above)
* grafana - Grafana metrics dashboard
* openattic - openATTIC Ceph management UI (ses5 only)
* suma - SUSE Manager (octopus only)

```
$ sesdev tunnel <deployment_id> dashboard
```

The command will output the URL that you can use to access the dashboard.

### Temporarily stop a cluster

A running cluster can be stopped by running the following command:

```
$ sesdev stop <deployment_id>
```

### Destroy a cluster

To remove a cluster (both the deployed VMs and the configuration), use the
following command:

```
$ sesdev destroy <deployment_id>
```

It has been reported that vagrant-libvirt sometimes leaves networks behind when
destroying domains (i.e. the VMs associated with a sesdev deployment). If this
bothers you, `sesdev destroy` has a `--destroy-networks` option you can use.

## Common pitfalls

This section describes some common pitfalls and how to resolve them.

### Domain about to create is already taken

#### Symptom

After deleting the `~/.sesdev` directory, `sesdev create` fails because
Vagrant throws an error message containing the words "domain about to create is
already taken".

#### Analysis

As described
[here](https://github.com/vagrant-libvirt/vagrant-libvirt/issues/658#issuecomment-335352340),
this typically occurs when the `~/.sesdev` directory is deleted. The libvirt
environment still has the domains, etc. whose metadata was deleted, and Vagrant
does not recognize the existing VM as one it created, even though the name is
identical.

#### Resolution

As described
[here](https://github.com/vagrant-libvirt/vagrant-libvirt/issues/658#issuecomment-380976825),
this can be resolved by manually deleting all the domains (VMs) and volumes
associated with the old deployment:

```
$ sudo virsh list --all
$ # see the names of the "offending" machines. For each, do:
$ sudo virsh destroy <THE_MACHINE>
$ sudo virsh undefine <THE_MACHINE>
$ sudo virsh vol-list default
$ # For each of the volumes associated with one of the deleted machines, do:
$ sudo virsh vol-delete --pool default <THE_VOLUME>
```

### Storage pool not found: no storage pool with matching name 'default'

#### Symptom

You run `ses create` but it does nothing and gives you a traceback ending with
an error:

```
libvirt.libvirtError: Storage pool not found: no storage pool with matching name 'default'
```

#### Analysis

For whatever reason, your libvirt deployment does not have a default pool
defined. You can verify this by doing:

```
$ sudo virsh pool-list
```

In a working deployment, it says:

```
 Name      State    Autostart
-------------------------------
 default   active   no
```

but in this case the "default" storage pool is missing. (One user hit this when
deploying sesdev on SLE-15-SP1.)

#### Resolution

The "libvirt-daemon" RPM owns a directory `/var/lib/libvirt/images` which is
intended to be associated with the default storage pool:

```
$ sudo rpm -qf /var/lib/libvirt/images
libvirt-daemon-5.1.0-lp151.7.6.1.x86_64
```

Assuming this directory exists and is empty, you can simply create a storage
pool called "default" that points to this directory, and the issue will be
resolved:

```
$ sudo virsh pool-define /dev/stdin <<EOF
<pool type='dir'>
  <name>default</name>
  <target>
    <path>/var/lib/libvirt/images</path>
  </target>
</pool>
EOF
$ sudo virsh pool-start default
$ sudo virsh pool-autostart default
```

Credits to Federico Simoncelli for the resolution, which I took from
[his post here](https://github.com/simon3z/virt-deploy/issues/8#issuecomment-73111541)

### When sesdev deployments get destroyed, virtual networks get left behind

#### Symptom

You create and destroy a sesdev deployment, perhaps even several
times, and then you notice that virtual networks get left behind. For example,
after several create/destroy cycles on deployment "foo":

```
$ sudo virsh net-list
 Name              State    Autostart   Persistent
----------------------------------------------------
 foo0              active   yes         yes
 foo1              active   yes         yes
 foo10             active   yes         yes
 foo2              active   yes         yes
 foo3              active   yes         yes
 foo4              active   yes         yes
 foo5              active   yes         yes
 foo6              active   yes         yes
 foo7              active   yes         yes
 foo8              active   yes         yes
 foo9              active   yes         yes
 vagrant-libvirt   active   no          yes
```

#### Analysis

It has been reported that vagrant-libvirt sometimes leaves networks behind when
it destroys domains (i.e. the VMs associated with a sesdev deployment). We do
not currently know why, or under what conditions, this happens.

#### Resolution

If this behavior bothers you, `sesdev destroy` has a `--destroy-networks` option
you can use. Of course, `sesdev destroy --destroy-networks` only works for the
network(s) associated with the VMs in the deployment being destroyed. To quickly
destroy a bunch of networks, construct a script like so:

```
#!/bin/bash
read -r -d '' NETZ <<EOF
foo0
foo1
foo2
foo3
foo4
foo5
foo6
foo7
foo8
foo9
foo10
EOF
for net in $NETZ ; do
    virsh net-destroy $net
    virsh net-undefine $net
done
```

The script should be run as root on the libvirt server.

## Contributing

If you would like to submit a patch to sesdev, please read the file
`CONTRIBUTING.rst` in the top-level directory of the source code distribution.
It can be found on-line here:

https://github.com/SUSE/sesdev/blob/master/CONTRIBUTING.rst
