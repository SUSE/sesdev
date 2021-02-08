#!/bin/bash

set -ex

# SES6 -> SES7 upgrade demo script

# Deploys a two node SES5 cluster capable of being upgraded to SES6, and
# upgrades it. It is recommended to capture stdout in a file when running, so
# one can go back and see what happened while the script was running.

DEP_ID="${1-ses5-to-ses6}"

function assert_cluster_health_ok {
    printf "=> asserting cluster health is OK... "
    ceph_health=$(sesdev ssh "$DEP_ID" master ceph health)
    if [ $ceph_health != "HEALTH_OK" ] ; then
        echo "not OK"
        sesdev ssh "$DEP_ID" master ceph status
        echo "Cluster not healthy after updating packages, aborting..." 1>&2
        exit 1
    fi
    echo "\tOK\n"
}

# Source venv if sesdev cannot be found
if ! which sesdev ; then
    source venv/bin/activate
    # TODO take path from upgrade-demo-ses5-to-ses6.sh script?
fi

echo
echo "=> destroy cluster from previous run (if any)" > /dev/null
sesdev destroy -f "$DEP_ID" || true

echo
echo "=> create a SES5 cluster" > /dev/null
sesdev create ses5 \
    --ram 8 \
    --cpus $(($(nproc)/2))  \
    --roles="[master], [storage,mon,mgr,mds,igw,rgw,nfs,openattic]" \
    --non-interactive \
    "$DEP_ID"

# untested yet
echo
echo "=> validate the previous step by demonstrating that the SES6 cluster is functional and healthy" > /dev/null
sesdev qa-test "$DEP_ID"

echo
echo "=> assert that master node is SLE-12-SP1/SES6"
sesdev ssh "$DEP_ID" master /home/vagrant/is_os.sh sles-12.3
# TODO validate ceph version?
sesdev ssh "$DEP_ID" master ceph versions
assert_cluster_health_ok

# Packages should only be updated through DeepSea, as only DeepSea is configured to prevent the
# installation of an updated node-exporter package that's not compatible with the stack.
# See https://github.com/SUSE/DeepSea/pull/1843/files for more info.
echo "=> running DeepSea stage 0"
sesdev ssh "$DEP_ID" master salt-run state.orch ceph.stage.0

assert_cluster_health_ok

echo
echo "=> upgrade the master node to SLE-15-SP1/SES6 (RPMs)" > /dev/null
sesdev upgrade "$DEP_ID" --to ses6 master
sesdev reboot "$DEP_ID" master

echo
echo "=> upgrade node1 to SLE-15-SP1/SES6 (RPMs)" > /dev/null
sesdev upgrade "$DEP_ID" --to ses6 node1
sesdev reboot "$DEP_ID" node1

sesdev ssh "$DEP_ID" master /home/vagrant/is_os.sh sles-12.3
sesdev ssh "$DEP_ID" master ceph versions
assert_cluster_health_ok

# TODO implement after upgrade steps before upgrading/migrating ceph

# sesdev ssh "$DEP_ID" master salt \* cmd.run 'bash -c "x=$(zypper ps -sss | wc -l) ; [ \${x} -eq 0 ]"'
# if [ $? -ne 0 ] ; then
    # reboot or restart services?
    # salt-run state.orch ceph.reboot # <- restarts services, may need to backfill after it ran
# fi

