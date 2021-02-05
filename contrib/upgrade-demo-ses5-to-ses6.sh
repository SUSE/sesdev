#!/bin/bash -ex

# SES6 -> SES7 upgrade demo script

# Deploys a minimal SES5 cluster capable of being upgraded to SES6, and upgrades
# it. It is recommended to capture stdout in a file when running, so one can go
# back and see what happened while the script was running.

DEP_ID="ses5-to-ses6"

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

ses6repos=<<EOF
[SUSE_CA]
name=SUSE Internal CA Certificate (SLE_15_SP1)
enabled=1
autorefresh=1
baseurl=http://download.suse.de/ibs/SUSE:/CA/SLE_15_SP1/
type=rpm-md
gpgcheck=1
gpgkey=http://download.suse.de/ibs/SUSE:/CA/SLE_15_SP1/repodata/repomd.xml.key

[base]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Basesystem/15-SP1/x86_64/product/
type=rpm-md

[custom-repo-1]
enabled=1
autorefresh=1
baseurl=http://download.suse.de/ibs/Devel:/Storage:/6.0:/Test/SLE_15_SP1/
type=rpm-md
gpgcheck=0

[devel-repo-1]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/Devel:/Storage:/6.0/images/repo/SUSE-Enterprise-Storage-6-POOL-x86_64-Media1/
type=rpm-md

[product]
enabled=1
autorefresh=1
baseurl=http://dist.suse.de/ibs/SUSE/Products/SLE-Product-SLES/15-SP1/x86_64/product/
type=rpm-md

[product-update]
enabled=1
autorefresh=1
baseurl=http://dist.suse.de/ibs/SUSE/Updates/SLE-Product-SLES/15-SP1/x86_64/update/
type=rpm-md

[server-apps]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/SUSE/Products/SLE-Module-Server-Applications/15-SP1/x86_64/product/
type=rpm-md

[server-apps-update]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Server-Applications/15-SP1/x86_64/update/
type=rpm-md

[storage]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/SUSE/Products/Storage/6/x86_64/product/
type=rpm-md

[storage-update]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/SUSE/Updates/Storage/6/x86_64/update/
type=rpm-md

[update]
enabled=1
autorefresh=1
baseurl=http://download.nue.suse.com/ibs/SUSE/Updates/SLE-Module-Basesystem/15-SP1/x86_64/update/
type=rpm-md
EOF

# sesdev ssh "$DEP_ID" master salt \* cmd.run 'bash -c "x=$(zypper ps -sss | wc -l) ; [ \${x} -eq 0 ]"'
# if [ $? -ne 0 ] ; then
    # reboot or restart services?
    # salt-run state.orch ceph.reboot # <- restarts services, may need to backfill after it ran
# fi

