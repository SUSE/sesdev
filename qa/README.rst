health-ok.sh
============

Script for validating Ceph clusters deployed using DeepSea and/or ceph-salt.


Overview
--------

This bash script contains integration tests for validating fresh Ceph
deployments.

The idea is to run this script with the appropriate arguments on the
Salt Master node after using DeepSea or ceph-salt to deploy a cluster.

The script makes a number of assumptions, as listed under "Assumptions", below.

On success (HEALTH_OK is reached, sanity tests pass), the script returns 0.
On failure, for whatever reason, the script returns non-zero.

The script produces verbose output on stdout, which can be captured for later
forensic analysis.

Though referred to as a bash script, ``health-ok.sh`` is only the entry point.
That file uses the bash internal ``source`` to run several helper scripts, which
are located in the ``common/`` subdirectory.


Assumptions
-----------

The script makes the following assumptions:

1. the script is being run on the Salt Master of a Ceph cluster deployed by
   DeepSea or ceph-salt
2. the script is being run as root
3. the Ceph admin keyring is installed in the usual way, so the root user can
   see and use the keyring


Caveats
-------

The following caveats apply:

1. Ceph will not work properly unless the nodes have (at least) short hostnames. That means the health-ok.sh script won't pass, either. There are two options: ``/etc/hosts`` or DNS


Linting
-------

When it comes to bash scripting, we run a tight ship. For linting, we use
ShellCheck [1] which can be installed in an openSUSE Leap 15.1 environment
by issuing the command:

    zypper -n install ShellCheck

To facilitate running ShellCheck on `health-ok.sh`, a script `shellcheck.sh` is provided.

[1] https://www.shellcheck.net/
