# sesdev - CLI tool to deploy and manage SES/Ceph clusters [![Build Status](https://travis-ci.org/SUSE/sesdev.svg?branch=master)](https://travis-ci.org/SUSE/sesdev)

`sesdev` is a CLI tool to deploy Ceph clusters (both the upstream and SUSE
downstream versions).

This tool uses [Vagrant](https://www.vagrantup.com/) behind the scenes to create
the VMs and run the deployment scripts.

## Installation

First, you should have both [QEMU](https://www.qemu.org/) and
[Libvirt](https://libvirt.org/) installed in some machine to host the VMs
created by sesdev (using Vagrant behind the scenes).

Installable packages for various Linux distributions like Fedora or openSUSE can
be found on the [openSUSE Build Service](https://software.opensuse.org//download.html?project=filesystems%3Aceph&package=sesdev)
(OBS).

### Installation on openSUSE

#### Install KVM/QEMU + Libvirt

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

#### Install sesdev from package

```
$ sudo zypper ar https://download.opensuse.org/repositories/filesystems:/ceph/<repo> filesystems_ceph
$ sudo zypper ar https://download.opensuse.org/repositories/Virtualization:/vagrant/<repo> vagrant_repo
$ sudo zypper ref
$ sudo zypper install sesdev
```

Where `<repo>` can be either `openSUSE_Leap_15.1` or `openSUSE_Tumbleweed`.

### Installation on Fedora Linux

#### Install KVM/QEMU + Libvirt

```
$ sudo dnf install qemu-common qemu-kvm libvirt-daemon-kvm \
libvirt-daemon libvirt-daemon-driver-qemu vagrant-libvirt
$ sudo systemctl enable libvirtd
$ sudo systemctl restart libvirtd
```

#### Install sesdev from package

```
$ sudo dnf config-manager --add-repo \
https://download.opensuse.org/repositories/home:rjdias/<distro>/home:rjdias.repo
dnf install sesdev
```

Where `<distro>` can be either `Fedora_29` or `Fedora_30`.

### Install sesdev from source

```
$ git clone https://github.com/SUSE/sesdev.git
$ cd sesdev
$ virtualenv --python=<path_to_python3> venv
$ source venv/bin/activate
$ pip install --editable .
```

Remember to re-run `pip install --editable .` after each git pull.

## Usage

Run `sesdev --help` or `sesdev <command> --help` to get check the available
options and description of the commands.

### Create/Deploy cluster

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
libvirt_host: <hostname|ip address>
```

Note that passwordless SSH access to this user@host combination needs to be
configured and enabled.

To create a multi-node Ceph cluster, you can specify the nodes and their roles
using the ``--roles`` option.

The roles of each node are grouped in square brackets, separated by commas. The
nodes are separated by commas, too.

The following roles can be assigned:

* `admin` - The admin node, running management components like the Salt master
  or openATTIC (SES5 only)
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

The following example will generate a cluster with 4 nodes: the admin node that
is running the salt-master and one MON, two storage nodes that will also run a
MON, a MGR and an MDS, and another node that will run an iSCSI gateway,
nfs-ganesha gateway, and an RGW gateway.

```
$ sesdev create nautilus --roles="[admin, mon], [storage, mon, mgr, mds], \
  [storage, mon, mgr, mds], [igw, ganesha, rgw]" big_cluster
```

#### Custom zypper repos

If you have the URL(s) of custom zypper repo(s) that you would like to add
to all the nodes of the cluster prior to deployment, add one or more
`--repo` options to the command line, e.g.:

```
$ sesdev create nautilus --single-node --repo [URL_OF_REPO] mini
```

By default, the custom repo(s) will be added with an elevated priority,
to ensure that packages from these repos will be installed even if higher
RPM versions of those packages exist. If this behavior is not desired,
add `--no-repo-priority` to disable it.

### Listing deployments

```
$ sesdev list
```

### SSH access to the cluster

```
$ sesdev ssh <deployment_id> [NODE]
```

Spawns an SSH shell to the admin node, or to node `NODE` if explicitly
specified. You can check the existing node names with the following command:

```
$ sesdev show <deployment_id>
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

### Stopping a cluster

A running cluster can be stopped by running the following command:

```
$ sesdev stop <deployment_id>
```

### Destroying a cluster

To remove a cluster (both the deployed VMs and the configuration), use the
following command:

```
$ sesdev destroy <deployment_id>
```
