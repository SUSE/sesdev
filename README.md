# sesdev - CLI tool to deploy and manage SES/Ceph clusters

## Usage

### Create/Deploy cluster

To create a single node Ceph cluster based on nautilus/leap-15.1:

```
$ sesdev create --single-node mini
```

The `mini` argument is the ID of the deployment. We can create many deployments by giving
different IDs.

To create a multi node Ceph cluster we can specify the roles of each node:

```
$ sesdev create --roles="[admin, mon], [storage, mon, mgr, mds], [storage, mon, mgr, mds], [igw, ganesha, rgw]" big_cluster

```

The cluster generated will have 4 nodes: the admin node that is running the salt-master and one
MON, two storage nodes that will also run a MON, a MGR and an MDS, and another node that will
run an iSCSI gateway, nfs-ganesha gateway, and an RGW gateway.

### Listing deployments

```
$ sesdev list
```

### SSH access to the cluster

```
$ sesdev ssh <deployment_id> [NODE]
```

Spawns an SSH shell to the admin node, or to node `NODE` if explicitly specified. You can check
the existing node names with the following command:

```
$ sesdev info <deployment_id>
```

### Services port-forwarding

It's possible to use an SSH tunnel to create a port-forwarding for a service running in the
cluster.
Currently only the dashboard service is implemented.

```
$ sesdev tunnel <deployment_id> dashboard
```

The command will output the URL that you can use to access the dashboard.