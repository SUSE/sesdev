#!/bin/bash -ex

# SES6 -> SES7 upgrade demo script

# Deploys a two node SES5 cluster capable of being upgraded to SES6, and
# upgrades it. It is recommended to capture stdout in a file when running, so
# one can go back and see what happened while the script was running.

DEP_ID="ses5-to-ses6"

# Source venv if sesdev cannot be found
if ! which sesdev ; then
    source venv/bin/activate
fi

echo
echo "=> destroy cluster from previous run (if any)" > /dev/null
sesdev destroy -f "$DEP_ID" || true

echo
echo "=> create a SES5 cluster" > /dev/null
sesdev create ses5 \
    --ram 8 \
    --cpus $(($(nproc)/2)) \
    --roles="[master], [storage,mon,mgr,mds,igw,rgw,nfs,openattic]" \
    --non-interactive \
    "$DEP_ID"

echo
echo "=> upgrading node packages"
sesdev ssh "$DEP_ID" master "zypper ref && zypper -n dup"
sesdev ssh "$DEP_ID" node1 "zypper ref && zypper -n dup"

echo "=> running DeepSea stage 0"
sesdev ssh "$DEP_ID" master salt-run state.orch ceph.stage.0

printf "=> checking cluster health"
ceph_health=$(sesdev ssh "$DEP_ID" master ceph health)
if [ $ceph_health != "HEALTH_OK" ] ; then
    printf "${ceph_health}\n"
    echo "Cluster not healthy after updating packages, aborting..." 1>&2
    exit 1
fi
printf "\tOK\n"

sesdev upgrade "$DEP_ID" --to ses6 master
sesdev upgrade "$DEP_ID" --to ses6 node1

# sesdev ssh "$DEP_ID" master salt \* cmd.run 'bash -c "x=$(zypper ps -sss | wc -l) ; [ \${x} -eq 0 ]"'
# if [ $? -ne 0 ] ; then
    # reboot or restart services?
    # salt-run state.orch ceph.reboot # <- restarts services, may need to backfill after it ran
# fi

