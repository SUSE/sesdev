#!/bin/bash
#
# NOTE: This is a work in progress!
#

set -x

FINAL_REPORT="$(mktemp)"

function final_report {
    echo -en "\n=====================================================================\n" >> $FINAL_REPORT
    cat $FINAL_REPORT
    rm $FINAL_REPORT
    exit 0
}

trap final_report INT

function run_cmd {
    local exit_status
    local timestamp="$(date -Iminutes --utc)"
    echo -en "\n${timestamp%+00:00}\n" >> $FINAL_REPORT
    echo -en "=====================================================================\n" >> $FINAL_REPORT
    echo -en "\nRunning command:\n\n    $@\n" >> $FINAL_REPORT
    $@
    exit_status="$?"
    echo -en "\nCompleted.\n" >> $FINAL_REPORT
    if [ "$exit_status" = "0" ] ; then
        echo -en "\nExit status: 0 (PASS)\n" >> $FINAL_REPORT
    else
        echo -en "\nExit status: $exit_status (FAIL)\n" >> $FINAL_REPORT
        final_report
    fi  
}

# ses5
run_cmd sesdev create ses5 --non-interactive --single-node --qa-test ses5-1node
run_cmd sesdev destroy --non-interactive ses5-1node
run_cmd sesdev create ses5 --non-interactive ses5-4node
run_cmd sesdev qa-test ses5-4node
run_cmd sesdev destroy --non-interactive ses5-4node

# nautilus
run_cmd sesdev create nautilus --non-interactive --single-node --qa-test nautilus-1node
run_cmd sesdev destroy --non-interactive nautilus-1node
run_cmd sesdev create nautilus --non-interactive nautilus-4node
run_cmd sesdev qa-test nautilus-4node
run_cmd sesdev destroy --non-interactive nautilus-4node

# ses6
run_cmd sesdev create ses6 --non-interactive --single-node --qa-test ses6-1node
run_cmd sesdev destroy --non-interactive ses6-1node
run_cmd sesdev create ses6 --non-interactive ses6-4node
run_cmd sesdev qa-test ses6-4node
run_cmd sesdev destroy --non-interactive ses6-4node

# octopus
run_cmd sesdev create octopus --non-interactive --single-node --qa-test octopus-1node
run_cmd sesdev destroy --non-interactive octopus-1node
run_cmd sesdev create octopus --non-interactive --ceph-salt-branch master --single-node --qa-test octopus-1node
run_cmd sesdev destroy --non-interactive octopus-1node
run_cmd sesdev create octopus --non-interactive --ceph-salt-branch master octopus-4node
run_cmd sesdev qa-test octopus-4node
run_cmd sesdev destroy --non-interactive octopus-4node

# ses7
run_cmd sesdev create ses7 --non-interactive --single-node --qa-test ses7-1node
run_cmd sesdev destroy --non-interactive ses7-1node
run_cmd sesdev create ses7 --non-interactive --ceph-salt-branch master --single-node --qa-test ses7-1node
run_cmd sesdev destroy --non-interactive ses7-1node
run_cmd sesdev create ses7 --non-interactive --ceph-salt-branch master ses7-4node
run_cmd sesdev qa-test ses7-4node
run_cmd sesdev destroy --non-interactive ses7-4node

# pacific
run_cmd sesdev create pacific --non-interactive --single-node --qa-test pacific-1node
run_cmd sesdev destroy --non-interactive pacific-1node
run_cmd sesdev create pacific --non-interactive --ceph-salt-branch master --single-node --qa-test pacific-1node
run_cmd sesdev destroy --non-interactive pacific-1node
run_cmd sesdev create pacific --non-interactive --ceph-salt-branch master pacific-4node
run_cmd sesdev qa-test pacific-4node
run_cmd sesdev destroy --non-interactive pacific-4node

# makecheck
run_cmd sesdev create makecheck --stop-before-run-make-check --ram 4
run_cmd sesdev create makecheck --non-interactive --os sles-12-sp3 --ceph-repo https://github.com/SUSE/ceph --ceph-branch ses5 --stop-before-run-make-check --ram 4
run_cmd sesdev create makecheck --non-interactive --os sles-15-sp1 --ceph-repo https://github.com/SUSE/ceph --ceph-branch ses6 --stop-before-run-make-check --ram 4
run_cmd sesdev create makecheck --non-interactive --os sles-15-sp2 --ceph-repo https://github.com/SUSE/ceph --ceph-branch ses7 --stop-before-run-make-check --ram 4

final_report
