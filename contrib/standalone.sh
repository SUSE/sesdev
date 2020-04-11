#!/bin/bash
#
# contrib/standalone.sh - sesdev regression testing
#
# NOTE: This is a work in progress!
#
# contrib/standalone.sh is a script which
#
# - deploys 1- and 4-node clusters of each of the main deployment types
#   (ses5, nautilus, ses6, octopus, ses7, pacific)
# - runs basic QA tests on each cluster after deployment is finished
# - if QA tests succeed, cluster is destroyed before moving on to the next one
# - when a failure occurs, the script aborts and post-mortem can be performed
#
# The script sends all output (its own and that of sesdev) to the screen,
# and there is typically so much of it that it will overflow any ordinary
# scrollback buffer. To facilitate capture of the output into a file for
# later analysis, a simple companion script is provided. See:
#
#     contrib/run-standalone.sh
#

set -x

SCRIPTNAME=$(basename ${0})
FINAL_REPORT="$(mktemp)"

function final_report {
    echo -en "\n=====================================================================\n" >> $FINAL_REPORT
    cat $FINAL_REPORT
    rm $FINAL_REPORT
    exit 0
}

trap final_report INT

function usage {
    echo "$SCRIPTNAME - sesdev regression testing"
    echo
    echo "Usage:"
    echo "    --help                   Display this usage message"
    echo "    --all                    Run all tests (the default)"
    echo "    --ceph-salt-from-source  Install ceph-salt from source"
    echo "                             (default: from RPM package)"
    echo "    --makecheck              Run makecheck (install-deps.sh,"
    echo "                             actually) tests"
    echo "    --nautilus               Run nautilus deployment tests"
    echo "    --octopus                Run octopus deployment tests"
    echo "    --pacific                Run pacific deployment tests"
    echo "    --ses5                   Run ses5 deployment tests"
    echo "    --ses6                   Run ses6 deployment tests"
    echo "    --ses7                   Run ses7 deployment tests"
    echo
    exit 1
}

function run_cmd {
    local exit_status
    local timestamp="$(date -Iminutes --utc)"
    echo -en "\n${timestamp%+00:00}\n" >> $FINAL_REPORT
    echo -en "=====================================================================\n" >> $FINAL_REPORT
    echo -en "Command:\n\n    $@\n" >> $FINAL_REPORT
    $@
    exit_status="$?"
    if [ "$exit_status" = "0" ] ; then
        echo -en "\nExit status: 0 (PASS)\n" >> $FINAL_REPORT
    else
        echo -en "\nExit status: $exit_status (FAIL)\n" >> $FINAL_REPORT
        final_report
    fi  
}

TEMP=$(getopt -o h \
--long "help,all,ceph-salt-from-source,makecheck,nautilus,octopus,pacific,ses5,ses6,ses7" \
-n 'standalone.sh' -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi
eval set -- "$TEMP"

# process command-line options
ALL="--all"
CEPH_SALT_FROM_SOURCE=""
MAKECHECK=""
NAUTILUS=""
OCTOPUS=""
PACIFIC=""
SES5=""
SES6=""
SES7=""
while true ; do
    case "$1" in
        --all)                   ALL="$1" ; shift ;;
        --ceph-salt-from-source) CEPH_SALT_FROM_SOURCE="--ceph-salt-branch=master" ; shift ;;
        --makecheck)             MAKECHECK="$1" ; shift ;;
        --nautilus)              NAUTILUS="$1" ; shift ;;
        --octopus)               OCTOPUS="$1" ; shift ;;
        --pacific)               PACIFIC="$1" ; shift ;;
        --ses5)                  SES5="$1" ; shift ;;
        --ses6)                  SES6="$1" ; shift ;;
        --ses7)                  SES7="$1" ; shift ;;
        -h|--help)               usage ;; # does not return
        --) shift ; break ;;
        *) echo "Internal error" ; exit 1 ;;
    esac
done

if [ "$MAKECHECK" -o "$NAUTILUS" -o "$OCTOPUS" -o "$PACIFIC" -o "$SES5" -o "$SES6" -o "$SES7" ] ; then
    ALL=""
fi

if [ "$ALL" ] ; then
    # MAKECHECK="--makecheck"
    NAUTILUS="--nautilus"
    OCTOPUS="--octopus"
    PACIFIC="--pacific"
    SES5="--ses5"
    SES6="--ses6"
    SES7="--ses7"
fi

if [ "$SES5" ] ; then
    run_cmd sesdev create ses5 --non-interactive --single-node --qa-test ses5-1node
    run_cmd sesdev destroy --non-interactive ses5-1node
    run_cmd sesdev create ses5 --non-interactive ses5-4node
    run_cmd sesdev qa-test ses5-4node
    run_cmd sesdev destroy --non-interactive ses5-4node
fi

if [ "$NAUTILUS" ] ; then
    run_cmd sesdev create nautilus --non-interactive --single-node --qa-test nautilus-1node
    run_cmd sesdev destroy --non-interactive nautilus-1node
    run_cmd sesdev create nautilus --non-interactive nautilus-4node
    run_cmd sesdev qa-test nautilus-4node
    run_cmd sesdev destroy --non-interactive nautilus-4node
fi

if [ "$SES6" ] ; then
    run_cmd sesdev create ses6 --non-interactive --single-node --qa-test ses6-1node
    run_cmd sesdev destroy --non-interactive ses6-1node
    run_cmd sesdev create ses6 --non-interactive ses6-4node
    run_cmd sesdev qa-test ses6-4node
    run_cmd sesdev destroy --non-interactive ses6-4node
fi

if [ "$OCTOPUS" ] ; then
    run_cmd sesdev create octopus --non-interactive $CEPH_SALT_FROM_SOURCE --single-node --qa-test octopus-1node
    run_cmd sesdev destroy --non-interactive octopus-1node
    run_cmd sesdev create octopus --non-interactive $CEPH_SALT_FROM_SOURCE octopus-4node
    run_cmd sesdev qa-test octopus-4node
    run_cmd sesdev destroy --non-interactive octopus-4node
fi

if [ "$SES7" ] ; then
    run_cmd sesdev create ses7 --non-interactive $CEPH_SALT_FROM_SOURCE --single-node --qa-test ses7-1node
    run_cmd sesdev destroy --non-interactive ses7-1node
    run_cmd sesdev create ses7 --non-interactive $CEPH_SALT_FROM_SOURCE ses7-4node
    run_cmd sesdev qa-test ses7-4node
    run_cmd sesdev destroy --non-interactive ses7-4node
fi

if [ "$PACIFIC" ] ; then
    run_cmd sesdev create pacific --non-interactive $CEPH_SALT_FROM_SOURCE --single-node --qa-test pacific-1node
    run_cmd sesdev destroy --non-interactive pacific-1node
    run_cmd sesdev create pacific --non-interactive $CEPH_SALT_FROM_SOURCE pacific-4node
    run_cmd sesdev qa-test pacific-4node
    run_cmd sesdev destroy --non-interactive pacific-4node
fi

if [ "$MAKECHECK" ] ; then
    # run_cmd sesdev create makecheck --non-interactive --stop-before-run-make-check --ram 4
    # run_cmd sesdev create makecheck --non-interactive --os sles-12-sp3 --ceph-repo https://github.com/SUSE/ceph --ceph-branch ses5 --stop-before-run-make-check --ram 4
    # run_cmd sesdev create makecheck --non-interactive --os sles-15-sp1 --ceph-repo https://github.com/SUSE/ceph --ceph-branch ses6 --stop-before-run-make-check --ram 4
    # run_cmd sesdev create makecheck --non-interactive --os sles-15-sp2 --ceph-repo https://github.com/SUSE/ceph --ceph-branch ses7 --stop-before-run-make-check --ram 4
    true
fi

final_report
