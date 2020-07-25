# sesdev - deploy and manage SES/Ceph clusters<br/>

`sesdev` is a CLI tool to deploy Ceph clusters (both the upstream and SUSE
downstream versions).

This tool uses [Vagrant](https://www.vagrantup.com/) behind the scenes to create
the VMs and run the deployment scripts.

## Build Status

### Travis

[![Travis Build Status](https://travis-ci.org/SUSE/sesdev.svg?branch=master)](https://travis-ci.org/SUSE/sesdev)

The Travis CI tests that the Python source code of `sesdev` compiles and has no
linter issues.

### Jenkins

[![Jenkins Build Status](https://ceph-ci.suse.de/job/sesdev-integration/job/master/badge/icon)](https://ceph-ci.suse.de/job/sesdev-integration/job/master/)

The Jenkins CI tests that `sesdev` can be used to deploy a single-node Ceph
15.2.x ("Octopus") cluster in an openSUSE Leap 15.2 environment.

## Table of Contents

[//]: # (To generate a new TOC, first install https://github.com/ekalinin/github-markdown-toc)
[//]: # (and then run "gh-md-toc README.md")
[//]: # (the new TOC will appear on stdout: the expectation is that the maintainer will do the rest.)

* [Installation](#installation)
   * [Install sesdev on openSUSE or SUSE Linux Enterprise](#install-sesdev-on-opensuse-or-suse-linux-enterprise)
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
   * [Create/deploy a Ceph cluster](#createdeploy-a-ceph-cluster)
      * [On a remote libvirt server via SSH](#on-a-remote-libvirt-server-via-ssh)
      * [Using salt instead of DeepSea/ceph-salt CLI](#using-salt-instead-of-deepseaceph-salt-cli)
      * [Without the devel repo](#without-the-devel-repo)
      * [With an additional custom zypper repo](#with-an-additional-custom-zypper-repo)
      * [With a set of custom zypper repos completely replacing the default repos](#with-a-set-of-custom-zypper-repos-completely-replacing-the-default-repos)
      * [With custom image paths](#with-custom-image-paths)
      * [With custom default roles](#with-custom-default-roles)
      * [config.yaml examples](#configyaml-examples)
         * [octopus from filesystems:ceph:octopus](#octopus-from-filesystemscephoctopus)
         * [octopus from filesystems:ceph:octopus&#8203;:upstream](#octopus-from-filesystemscephoctopusupstream)
         * [ses7 from Devel:Storage:7.0](#ses7-from-develstorage70)
         * [ses7 from Devel:Storage:7.0:CR](#ses7-from-develstorage70cr)
   * [List existing deployments](#list-existing-deployments)
   * [SSH access to a cluster](#ssh-access-to-a-cluster)
   * [Copy files into and out of a cluster](#copy-files-into-and-out-of-a-cluster)
   * [Services port-forwarding](#services-port-forwarding)
   * [Replace ceph-salt](#replace-ceph-salt)
   * [Replace MGR modules](#replacing-mgr-modules)
   * [Add a repo to a cluster](#add-a-repo-to-a-cluster)
   * [Temporarily stop a cluster](#temporarily-stop-a-cluster)
   * [Destroy a cluster](#destroy-a-cluster)
   * [Run "make check"](#run-make-check)
      * [Run "make check" on Tumbleweed from upstream "master" branch](#run-make-check-on-tumbleweed-from-upstream-master-branch)
      * [Run "make check" on openSUSE Leap 15.2 from upstream "octopus" branch](#run-make-check-on-opensuse-leap-152-from-upstream-octopus-branch)
      * [Run "make check" on SLE-15-SP2 from downstream "ses7" branch](#run-make-check-on-sle-15-sp2-from-downstream-ses7-branch)
      * [Other "make check" scenarios](#other-make-check-scenarios)
* [Common pitfalls](#common-pitfalls)
   * [Domain about to create is already taken](#domain-about-to-create-is-already-taken)
   * [Storage pool not found: no storage pool with matching name 'default'](#storage-pool-not-found-no-storage-pool-with-matching-name-default)
   * [When sesdev deployments get destroyed, virtual networks get left behind](#when-sesdev-deployments-get-destroyed-virtual-networks-get-left-behind)
   * ["Failed to connect socket" error when attempting to use remote libvirt server](#failed-to-connect-socket-error-when-attempting-to-use-remote-libvirt-server)
   * [mount.nfs: Unknown error 521](#mountnfs-unknown-error-521)
* [Contributing](#contributing)


## Installation

First, you should have both [QEMU](https://www.qemu.org/) and
[Libvirt](https://libvirt.org/) installed in some machine to host the VMs
created by sesdev (using Vagrant behind the scenes).

Installable packages for various Linux distributions like Fedora or openSUSE can
be found on the [openSUSE Build Service](https://software.opensuse.org//download.html?project=filesystems%3Aceph&package=sesdev)
(OBS).

### Install sesdev on openSUSE or SUSE Linux Enterprise

#### Install KVM/QEMU and Libvirt

Run the following commands as root:

```
# zypper -n install -t pattern kvm_server kvm_tools
# systemctl enable libvirtd
# systemctl restart libvirtd
```

#### Add user to libvirt group

If you are running libvirt on the same machine where you installed sesdev, add
your user to the "libvirt" group to avoid "no polkit agent available" errors
when vagrant attempts to connect to the libvirt daemon:

```
# groupadd libvirt
groupadd: group 'libvirt' already exists
# usermod -a -G libvirt $USER
```

Log out, and then log back in. You should now be a member of the "libvirt"
group.

#### Install Vagrant

sesdev needs Vagrant to work. To install Vagrant, run the following commands as
root:

```
# zypper ar https://download.opensuse.org/repositories/Virtualization:/vagrant/<repo> vagrant_repo
# zypper ref
# zypper -n install vagrant vagrant-libvirt
```

Where `<repo>` can be any of the openSUSE build targets currently enabled for
the [Virtualization:vagrant/vagrant package in the openSUSE Build Service](https://build.opensuse.org/package/show/Virtualization:vagrant/vagrant).

#### Install sesdev from package

sesdev itself can be installed either from package or from source. If you
prefer to install from package, follow the instructions in this section. If you
prefer to install from source, skip down to the "Install sesdev from source"
section.

Run the following commands as root:

```
# zypper ar https://download.opensuse.org/repositories/filesystems:/ceph/<repo> filesystems_ceph
# zypper ref
# zypper install sesdev
```

Where `<repo>` can be any of the openSUSE build targets currently enabled for
the [sesdev package in the openSUSE Build Service](https://build.opensuse.org/package/show/filesystems:ceph/sesdev).

At this point, sesdev should be installed and ready to use: refer to the
[Usage](#usage) chapter, below, for further information.

### Install sesdev on Fedora Linux

#### Install KVM/QEMU and Libvirt

Run the following commands as root:

```
# dnf install qemu-common qemu-kvm libvirt-daemon-kvm \
libvirt-daemon libvirt-daemon-driver-qemu vagrant-libvirt
# systemctl enable libvirtd
# systemctl restart libvirtd
```

#### Install sesdev from package

Run the following commands as root:

```
# dnf config-manager --add-repo \
https://download.opensuse.org/repositories/filesystems:/ceph/<distro>/filesystems:ceph.repo
# dnf install sesdev
```

Where `<distro>` can be any of the Fedora build targets currently enabled for
the [sesdev package in the openSUSE Build Service](https://build.opensuse.org/package/show/filesystems:ceph/sesdev).

At this point, sesdev should be installed and ready to use: refer to the
[Usage](#usage) chapter, below, for further information.

### Install sesdev on Debian/Ubuntu

sesdev is known to work on recent Ubuntu versions, but there is no package
for it: you have to install from source. Follow the instructions given in
[Install sesdev from source](#install-sesdev-from-source).

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

#### openSUSE

```
# zypper -n install gcc git-core libvirt-devel python3-devel python3-virtualenv
```

#### Debian / Ubuntu

```
# apt-get install -y git gcc libvirt-dev \
virtualenv python3-dev python3-venv python3-virtualenv
```

#### Fedora

```
# dnf install -y git-core gcc libvirt-devel \
python3-devel python3-virtualenv
```

Now you can proceed to clone the sesdev source code repo and bootstrap it:

```
$ git clone https://github.com/SUSE/sesdev.git
$ cd sesdev
$ ./bootstrap.sh
```

Before you can use `sesdev`, you need to activate the Python virtual environment
created by the `bootstrap.sh` script. The script tells you how to do this, but
we'll give the command here, anyway:

```
source venv/bin/activate
```

At this point, sesdev should be installed and ready to use: refer to the
[Usage](#usage) chapter, below, for further information.

To leave the virtual environment, simply run:

```
deactivate
```

CAVEAT: Remember to re-run `./bootstrap.sh` after each git pull.

#### Running the unit tests

If you are preparing a code change for submission and would like to run the
unit tests on it, make sure you have installed sesdev from source, as described
above, and the virtualenv is active. Then, follow the instructions below.

First, install the "tox" package in your system:

#### openSUSE

```
zypper -n install python3-tox
```

#### Debian / Ubuntu

```
apt-get install -y tox
```

#### Fedora

```
dnf install -y python3-tox
```

Then, execute the following commands in the top-level of your local git clone
to install the dependencies, including test dependencies:

```
source venv/bin/activate
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

### Create/deploy a Ceph cluster

To create a single node Ceph cluster based on nautilus/leap-15.1 on your local
system, run the following command:

```
$ sesdev create nautilus --single-node mini
```

The `mini` argument is the ID of the deployment. It is optional: if you omit it,
sesdev will assign an ID as it sees fit. You can create many deployments by
giving them different IDs.

To create a multi-node Ceph cluster, you can specify the nodes and their roles
using the `--roles` option.

The roles of each node are grouped in square brackets, separated by commas. The
nodes are separated by commas, too.

The following roles can be assigned:

* `master` - The master node, running management components like the Salt master
* `admin` - signifying that the node should get ceph.conf and keyring [1]
* `bootstrap` - The node where `cephadm bootstrap` will be run
* `client` - Various Ceph client utilities
* `nfs` - NFS (Ganesha) gateway [2]
* `grafana` - Grafana metrics visualization (requires Prometheus) [3]
* `igw` - iSCSI target gateway
* `mds` - CephFS MDS
* `mgr` - Ceph Manager instance
* `mon` - Ceph Monitor instance
* `prometheus` - Prometheus monitoring [3]
* `rgw` - Ceph Object Gateway
* `storage` - OSD storage daemon [4]
* `suma` - SUSE Manager (octopus only)

[1] CAVEAT: sesdev applies the `admin` role to all nodes, regardless of whether
or not the user specified it explicitly on the command line or in `config.yaml`.

[2] The `nfs` role may also be used when deploying a CaaSP cluster. In that
case we get a node acting as an NFS server as well as a pod running in the k8s
cluster and acting as an NFS client, providing a persistent store for other
(containerized) applications.

[3] CAVEAT: Do not specify `prometheus`/`grafana` roles for ses5 deployments.
The DeepSea version shipped with SES5 always deploys Prometheus and Grafana
instances on the master node, but does not recognize `prometheus`/`grafana`
roles in `policy.cfg`.

[4] Please note that we do not need the `storage` role when we plan to deploy
Rook/Ceph over CaaSP. By default, Rook creates OSD pods which take over any
spare block devices in worker nodes, i.e., all block devices but the first
(OS disk) of any given worker.

The following example will generate a cluster with four nodes: the master (Salt
Master) node that is also running a MON daemon; a storage (OSD) node that
will also run a MON, a MGR and an MDS and serve as the bootstrap node; another
storage (OSD) node with MON, MGR, and MDS; and a fourth node that will run an iSCSI
gateway, an NFS (Ganesha) gateway, and an RGW gateway.

```
$ sesdev create nautilus --roles="[master, mon], [bootstrap, storage, mon, mgr, mds], \
  [storage, mon, mgr, mds], [igw, nfs, rgw]"
```

#### On a remote libvirt server via SSH

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

#### Using salt instead of DeepSea/ceph-salt CLI

By default, sesdev will use the DeepSea CLI to run the DeepSea Stages (ses5,
nautilus, ses6) or the "ceph-salt" command to apply the ceph-salt Salt Formula
(ses7, octopus, pacific).

If you would rather use Salt directly, give the `--salt` option on the `sesdev
create` command line.

#### Without the devel repo

The "core" deployment targets (ses5, nautilus, ses6, octopus, ses7, pacific)
all have a concept of a "devel" repo where updates to the Ceph/storage-related
packages are staged. Since users frequently want to install the "latest,
greatest" packages, the "devel" repo is added to all nodes by default. However,
there are times when this is not desired: when using sesdev to simulate
update/upgrade scenarios, for example.

To deploy a Ceph cluster without the "devel" repo, give the `--product` option
on the `sesdev create` command line.

#### With an additional custom zypper repo

Each deployment version (e.g. "octopus", "nautilus") is associated with
a set of zypper repos which are added on each VM that is created.

There are times when you may need to add additional zypper repo(s)
to all the VMs prior to deployment. In such a case, add one or more `--repo`
options to the command line, e.g.:

```
$ sesdev create nautilus --single-node --repo [URL_OF_REPO]
```

By default, the custom repo(s) will be added with an elevated priority,
to ensure that packages from these repos will be installed even if higher
RPM versions of those packages exist. If this behavior is not desired,
add `--no-repo-priority` to disable it.

#### With a set of custom zypper repos completely replacing the default repos

If the default zypper repos that are added to each VM prior to deployment are
completely wrong for your use case, you can override them via
`~/.sesdev/config.yaml`.

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

#### With custom image paths

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

#### With custom default roles

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

This is the default, so no tweaking of config.yaml is necessary. Just:

```
sesdev create octopus
```

##### octopus from filesystems:ceph:octopus&#8203;:upstream

Run `sesdev create octopus` with the following options:

```
sesdev create octopus \
    --repo-priority \
    --repo https://download.opensuse.org/repositories/filesystems:/ceph:/octopus:/upstream/openSUSE_Leap_15.2 \
    --image-path registry.opensuse.org/filesystems/ceph/octopus/upstream/images/ceph/ceph
```

Alternatively, add the following to your `config.yaml` to always use these
options when deploying `octopus` clusters:

```
version_os_repo_mapping:
    octopus:
        leap-15.2:
            - 'https://download.opensuse.org/repositories/filesystems:/ceph:/octopus/openSUSE_Leap_15.2'
            - '96!https://download.opensuse.org/repositories/filesystems:/ceph:/octopus:/upstream/openSUSE_Leap_15.2'
image_paths:
    octopus: 'registry.opensuse.org/filesystems/ceph/octopus/upstream/images/ceph/ceph'
```

Note: The elevated priority on the `filesystems:ceph:octopus:upstream`
repo is needed to ensure that the ceph package from that project gets installed
even if RPM evaluates its version number to be lower than that of the ceph
packages in the openSUSE Leap 15.2 base and `filesystems:ceph:octopus` repos.

##### ses7 from Devel:Storage:7.0

This is the default, so no tweaking of config.yaml is necessary. Just:

```
sesdev create ses7
```

Note that this will work even if there is no ceph package visible at
https://build.suse.de/project/show/Devel:Storage:7.0 since it uses the
installation media repo, not the "SLE_15_SP2" repo.

##### ses7 from Devel:Storage:7.0:CR

The ceph package in `Devel:Storage:7.0:CR` has the same version as
the one in `filesystems:ceph:master:upstream`, so the procedure for
using it is similar:

```
sesdev create ses7 \
    --repo-priority \
    --repo http://download.suse.de/ibs/Devel:/Storage:/7.0:/CR/SLE_15_SP2/ \
    --image-path registry.suse.de/devel/storage/7.0/cr/containers/ses/7/ceph/ceph
```

Alternatively, add the following to your `config.yaml` to always use
these options when deploying `ses7` clusters:

```
version_os_repo_mapping:
    ses7:
        sles-15-sp2:
            - 'http://download.suse.de/ibs/SUSE:/SLE-15-SP2:/Update:/Products:/SES7/images/repo/SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
            - 'http://download.suse.de/ibs/Devel:/Storage:/7.0/images/repo/SUSE-Enterprise-Storage-7-POOL-x86_64-Media1/'
            - '96!http://download.suse.de/ibs/Devel:/Storage:/7.0:/CR/SLE_15_SP2/'
image_paths:
    ses7: 'registry.suse.de/devel/storage/7.0/cr/containers/ses/7/ceph/ceph'
```

Note: The elevated priority on the `Devel:Storage:7.0:CR` repo is needed to
ensure that the ceph package from that project gets installed even if RPM
evaluates its version number to be lower than that of the ceph packages in the
SES7 Product and `Devel:Storage:7.0` repos.

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

### Replace ceph-salt

For deployments that used ceph-salt, it's possible to replace the ceph-salt
installed by sesdev with a different one:

```
$ sesdev replace-ceph-salt --local <path> <deployment_id>
```

Assuming `<path>` points to ceph-salt source code, the command will work
regardless of whether ceph-salt was originally installed from source or
from RPM.

### Replace MGR modules

It's possible to replace Ceph MGR modules with a version found in a github PR,
git branch or in a local repository.

This can be helpful to test PRs in a cluster with all services enabled.

```
$ sesdev replace-mgr-modules <deployment_id> <pr>
```

### Add a repo to a cluster

A custom repo can be added to all nodes of a running cluster using the following
command:

```
$ sesdev add-repo <deployment_id> <repo_url>
```

If the repo URL is omitted, the "devel" repo (as defined for the Ceph version 
deployed) will be added.

If you want to also update packages on all nodes to the versions in that repo,
give the `--update` option. For example, one can test an update scenario by
deploying a cluster with the `--product` option and then updating the cluster to
the packages staged in the "devel" project:

```
$ sesdev add-repo --update <deployment_id>
```

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

### Run "make check"

If your libvirtd machine has enough memory, you can use sesdev to run "make
check" in various environments. Use

```
$ sesdev create makecheck --help
```

to see the available options.

RAM CAVEAT: the default RAM amount for the makecheck might not be sufficient.
If you have plenty of memory on your libvirtd machine, running with higher
values of `--ram` (the higher, the better) is recommended.

CPUS CAVEAT: using the `--cpus` option, it is also possible increase the number
of (virtual) CPUs available for the build, but values greater than four have not
been well tested.

The `sesdev create makecheck` command will (1) deploy a VM, (2) create an
"ordinary" (non-root) user with passwordless sudo privileges and, as this
user (3) clone the specified Ceph repo and check out the specified branch,
(4) run `install-deps.sh`, and (5) run `run-make-check.sh`.

The following sub-sections provide instructions on how to reproduce some
common "make check" scenarios.

#### Run "make check" on Tumbleweed from upstream "master" branch

This is the default. Just:

```
$ sesdev create makecheck
```

#### Run "make check" on openSUSE Leap 15.2 from upstream "octopus" branch

```
$ sesdev create makecheck --os leap-15.2 --ceph-branch octopus
```

(It is not necessary to give `--ceph-repo https://github.com/ceph/ceph` here,
since that is the default.)

#### Run "make check" on SLE-15-SP2 from downstream "ses7" branch

```
$ sesdev create makecheck --os sles-15-sp2 \
      --ceph-repo https://github.com/SUSE/ceph \
      --ceph-branch ses7
```

#### Other "make check" scenarios

More combinations are supported than are described here. Compiling
the respective `sesdev create makecheck` commands for these environments is left
as an exercise for the reader.


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
associated with the old deployment (note: the commands must be run as root):

```
# virsh list --all
# # see the names of the "offending" machines. For each, do:
# virsh destroy <THE_MACHINE>
# virsh undefine <THE_MACHINE>
# virsh vol-list default
# # For each of the volumes associated with one of the deleted machines, do:
# virsh vol-delete --pool default <THE_VOLUME>
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
defined. You can verify this by running the following command as root:

```
# virsh pool-list
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
# rpm -qf /var/lib/libvirt/images
libvirt-daemon-5.1.0-lp151.7.6.1.x86_64
```

Assuming this directory exists and is empty, you can simply create a storage
pool called "default" that points to this directory, and the issue will be
resolved (run the commands as root):

```
# virsh pool-define /dev/stdin <<EOF
<pool type='dir'>
  <name>default</name>
  <target>
    <path>/var/lib/libvirt/images</path>
  </target>
</pool>
EOF
# virsh pool-start default
# virsh pool-autostart default
```

Credits to Federico Simoncelli for the resolution, which I took from
[his post here](https://github.com/simon3z/virt-deploy/issues/8#issuecomment-73111541)

### When sesdev deployments get destroyed, virtual networks get left behind

#### Symptom

You create and destroy a sesdev deployment, perhaps even several
times, and then you notice that virtual networks get left behind. For example,
after several create/destroy cycles on deployment "foo":

```
# virsh net-list
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
destroy a bunch of networks, construct a script like this one:

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

An unsupported, user-contributed version of this script -- `contrib/nukenetz.sh`
-- can be found in the source-code tree.

### "Failed to connect socket" error when attempting to use remote libvirt server

#### Symptom

When attempting to create or list deployments on a remote libvirt/SSH server,
sesdev barfs out a Python traceback ending in:

```
libvirt.libvirtError: Failed to connect socket to
'/var/run/libvirt/libvirt-sock': No such file or directory
```

#### Analysis

When told to use remote libvirt/SSH, sesdev expects that there won't be any
libvirtd instance running locally. This Python traceback is displayed when

1. sesdev is configured to use remote libvirt/SSH, **and**
2. libvirtd.service is running locally

#### Resolution

Stop the local libvirtd.service.

### mount.nfs: Unknown error 521

#### Symptom

When the `--synced-folder` option is provided, the deployment fails with
something like:

    mount -o vers=3,udp 192.168.xxx.xxx:/home/$USER/.sesdev/$NAME /$PATH

    Stderr from the command:

    mount.nfs: Unknown error 521

#### Analysis

This indicates that your nfs-server is not working properly or hasn't started yet.

#### Resolution

Please make sure that your nfs-server is up and running without errors:

```
# systemctl status nfs-server
```

If this doesn't report back with `active`, please consider running:

```
# systemctl restart nfs-server
# systemctl enable nfs-server
```

## Contributing

If you would like to submit a patch to sesdev, please read the file
`CONTRIBUTING.rst` in the top-level directory of the source code distribution.
It can be found on-line here:

https://github.com/SUSE/sesdev/blob/master/CONTRIBUTING.rst

