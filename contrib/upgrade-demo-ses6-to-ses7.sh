#!/bin/bash -ex

# SES6 -> SES7 upgrade demo script

# Deploys a minimal SES6 cluster capable of being upgraded to SES7, and upgrades
# it. It is recommended to capture stdout in a file when running, so one can go
# back and see what happened while the script was running.

# TODO:
# - after each step, programatically validate that the step actually did what it
#   was supposed to do

DEP_ID="ses6-to-ses7"

echo
echo "=> destroy cluster from previous run (if any)" > /dev/null
sesdev destroy -f "$DEP_ID" || true

echo
echo "=> create a SES6 cluster" > /dev/null
sesdev create ses6 \
    --roles="[admin,master],[admin,mon,mgr,storage],[admin,mon,mgr,storage],[admin,mon,mgr,storage]" \
    --non-interactive \
    "$DEP_ID"

echo
echo "=> validate the previous step by demonstrating that the SES6 cluster is functional and healthy" > /dev/null
sesdev qa-test "$DEP_ID"

echo
echo "=> assert that master node is SLE-15-SP1/SES6"
sesdev ssh "$DEP_ID" master /home/vagrant/is_os.sh sles-15.1
sesdev ssh "$DEP_ID" master ceph versions
sesdev ssh "$DEP_ID" master ceph status

echo
echo "=> upgrade the Salt Master node to SLE-15-SP2/SES7 (RPMs)" > /dev/null
sesdev upgrade "$DEP_ID" master --to ses7
sesdev reboot "$DEP_ID" master

echo
echo "=> assert that master node is SLE-15-SP2/SES7"
sesdev ssh "$DEP_ID" master /home/vagrant/is_os.sh sles-15.2
sesdev ssh "$DEP_ID" master ceph versions
# TODO: validate 15.2.x
sesdev ssh "$DEP_ID" master ceph health
# TODO: validate HEALTH_OK

echo
echo "=> disable DeepSea stages in DeepSea pillar data" > /dev/null
sesdev ssh "$DEP_ID" master "bash -c 'echo -en stage_prep: disabled\\\nstage_discovery: disabled\\\nstage_configure: disabled\\\nstage_deploy: disabled\\\nstage_services: disabled\\\nstage_remove: disabled\\\n >> /srv/pillar/ceph/stack/global.yml'"

echo
echo "=> configure ses7_container_registries in DeepSea pillar data" > /dev/null
sesdev ssh "$DEP_ID" master "bash -c 'echo -en ses7_container_image: registry.suse.de/devel/storage/7.0/containers/ses/7/ceph/ceph\\\nses7_container_registries:\\\n \\ - location: registry.suse.de/devel/storage/7.0/containers/ses/7/ceph/ceph\\\n \\ \\ \\ insecure: true\\\n >> /srv/pillar/ceph/stack/global.yml'"

echo "=> dump new pillar settings and refresh pillar" > /dev/null
sesdev ssh "$DEP_ID" master cat /srv/pillar/ceph/stack/global.yml
sesdev ssh "$DEP_ID" master "bash -c 'salt \\* saltutil.refresh_pillar'"

# TODO: attempt to run a deepsea stage, validate that it fails

echo
echo "=> assimilate /etc/ceph/ceph.conf into MON Config Store" > /dev/null
sesdev ssh "$DEP_ID" master "bash -c 'ceph config assimilate-conf -i /etc/ceph/ceph.conf'"

# TODO: dump config store, check that settings expected to be populated are
# populated, use /etc/ceph/ceph.conf parsing tool to compare

echo
echo "=> display cluster upgrade and health status" > /dev/null
sesdev ssh "$DEP_ID" master salt-run upgrade.status
# TODO: parse output of upgrade.status and compare actual with expected output
sesdev ssh "$DEP_ID" master ceph health
# TODO: assert HEALTH_OK

function ping_salt_minion {
    set +x
    local minion="$1"
    local seconds_to_wait
    seconds_to_wait="600"
    local interval_seconds
    interval_seconds="15"
    echo
    echo "=> waiting up to $seconds_to_wait seconds for minion $minion to respond to ping"
    while true ; do
        if sesdev ssh "$DEP_ID" master "bash -x -c 'salt $minion test.ping'" ; then
            break
        fi
        echo
        echo "=> $minion did not respond to ping"
        seconds_to_wait="$(( seconds_to_wait - interval_seconds ))"
        echo
        echo "=> waiting up to $seconds_to_wait more seconds for minion $minion to respond to ping"
        if [ "$seconds_to_wait" -le "0" ] ; then
            echo "ERROR: timeout expired with minion $minion still not responding to ping"
            exit 1
        fi
        sleep "$interval_seconds"
    done
    echo
    echo "=> minion $minion responded to ping"
    set -x
}

function upgrade_node {
    local node_short_hostname="$1"
    echo
    echo "=> upgrade $node_short_hostname of the Ceph cluster to SLE-15-SP2/SES7 RPMs" > /dev/null
    sesdev upgrade "$DEP_ID" "$node_short_hostname" --to ses7
    sesdev reboot "$DEP_ID" "$node_short_hostname"
    ping_salt_minion "${node_short_hostname}.${DEP_ID}.test" 
    
    echo
    echo "=> complete upgrade of $node_short_hostname of the Ceph cluster" > /dev/null
    sesdev ssh "$DEP_ID" master salt "${node_short_hostname}.${DEP_ID}.test" state.apply ceph.upgrade.ses7.adopt
    # TODO: compare actual with expected output

    echo
    echo "=> assert that $node_short_hostname is now running SLE-15-SP2" /dev/null
    sesdev ssh "$DEP_ID" "$node_short_hostname" /home/vagrant/is_os.sh sles-15.2

    echo
    echo "=> display cluster upgrade and health status" > /dev/null
    sesdev ssh "$DEP_ID" master salt-run upgrade.status
    # TODO: compare actual with expected output
    sesdev ssh "$DEP_ID" master ceph health
    # TODO: compare actual with expected output (probably won't be HEALTH_OK)
}

echo
echo "=> BEGIN: upgrade node1"
sesdev ssh "$DEP_ID" master ceph osd add-noout node1
# TODO: compare actual with expected output
upgrade_node node1
sesdev ssh "$DEP_ID" master ceph osd rm-noout node1
# TODO: compare actual with expected output
echo
echo "=> END: upgrade node1"

echo
echo "=> BEGIN: upgrade node2"
sesdev ssh "$DEP_ID" master ceph osd add-noout node2
# TODO: compare actual with expected output
upgrade_node node2
sesdev ssh "$DEP_ID" master ceph osd rm-noout node2
# TODO: compare actual with expected output
echo
echo "=> END: upgrade node2"

echo
echo "=> BEGIN: upgrade node3"
sesdev ssh "$DEP_ID" master ceph osd add-noout node3
# TODO: compare actual with expected output
upgrade_node node3
sesdev ssh "$DEP_ID" master ceph osd rm-noout node3
# TODO: compare actual with expected output
echo
echo "=> END: upgrade node3"

echo
echo "=> fully upgraded SES7 cluster" > /dev/null
sesdev ssh "$DEP_ID" master ceph status

echo
echo "=> export cluster configuration from deepsea" > /dev/null
sesdev ssh "$DEP_ID" master "bash -x -c 'salt-run upgrade.ceph_salt_config > ceph-salt-config.json'"
sesdev ssh "$DEP_ID" master "bash -x -c 'salt-run upgrade.generate_service_specs > specs.yaml'"
# TODO: validation (?)

echo
echo "=> remove deepsea, install ceph-salt" > /dev/null
sesdev ssh "$DEP_ID" master "bash -x -c 'zypper --non-interactive rm deepsea deepsea-cli'"
sesdev ssh "$DEP_ID" master "bash -x -c 'zypper --non-interactive install ceph-salt'"
sesdev ssh "$DEP_ID" master "bash -x -c 'systemctl restart salt-master.service'"
sesdev ssh "$DEP_ID" master "bash -x -c 'salt \\* saltutil.sync_all'"
# TODO: validation (?)

echo
echo "=> import and apply ceph-salt config" > /dev/null
sesdev ssh "$DEP_ID" master "bash -x -c 'ceph-salt import ceph-salt-config.json'"
sesdev ssh "$DEP_ID" master "bash -x -c 'ceph-salt config /ssh generate'"
sesdev ssh "$DEP_ID" master "bash -x -c 'ceph-salt config ls'"
# TODO: compare actual with expected output
sesdev ssh "$DEP_ID" master "bash -x -c 'ceph-salt apply'"
# TODO: validation (?)
