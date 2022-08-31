#!/bin/bash
#
# contrib/standalone.sh - sesdev regression testing
#
# NOTE: This is a work in progress!
#
# contrib/standalone.sh is a script which
#
# - deploys 1- and 4-node clusters of each of the main deployment types
#   (nautilus, ses6, octopus, ses7, pacific)
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

SCRIPTNAME="$(basename "$0")"
CONFIG_YAML="$HOME/.sesdev/config.yaml"
FINAL_REPORT="$(mktemp)"
TEMP_FILE="$(mktemp)"
CMD_OUTPUT="$(mktemp)"

function final_report {
    echo -en "\n=====================================================================\n" >> "$FINAL_REPORT"
    cat "$FINAL_REPORT"
    rm "$FINAL_REPORT"
    rm "$TEMP_FILE"
    rm "$CMD_OUTPUT"
    rm -f "$CONFIG_YAML"
    exit 0
}

trap final_report INT

function usage {
    echo "$SCRIPTNAME - sesdev regression testing"
    echo
    echo "Usage:"
    echo
    echo "    $ contrib/standalone.sh"
    echo
    echo "By default, runs regression tests of sesdev's ability to deploy Ceph"
    echo "on supported OSes/OS versions."
    echo
    echo "Options:"
    echo "    --help                   Display this usage message"
    echo "    --ceph-salt-branch       Branch from which to install ceph-salt from source"
    echo "    --ceph-salt-repo         Repo from which to install ceph-salt from source"
    echo "    --full                   Run all tests, including makecheck"
    echo "    --makecheck              Run makecheck (install-deps.sh, actually)"
    echo "                             tests"
    echo "    --nautilus               Run nautilus deployment tests"
    echo "    --no-stop-on-failure     Continue script execution if there is a"
    echo "                             failure (default: stop immediately)."
    echo "    --octopus                Run octopus deployment tests"
    echo "    --pacific                Run pacific deployment tests"
    echo "    --ses6                   Run ses6 deployment tests"
    echo "    --ses7                   Run ses7 deployment tests"
    echo
}

function expect_fail {
    "$@"
    exit_status="$1"
    if [ "$exit_status" = "0" ] ; then
        return 1
    else
        return 0
    fi
}

function run_cmd {
    local exit_status
    local timestamp
    timestamp="$(date -Iminutes --utc)"
    {
        echo -en "\n${timestamp%+00:00}\n" ;
        echo -en "=====================================================================\n" ;
        echo -en "Command:\n\n    $*\n"
    } >> "$FINAL_REPORT"
    true > "$CMD_OUTPUT"
    "$@" | tee "$CMD_OUTPUT"
    exit_status="${PIPESTATUS[0]}"
    if [ "$exit_status" != "0" ] ; then
        echo -en "\nExit status: $exit_status (FAIL)\n" >> "$FINAL_REPORT"
        [ "$STOP_ON_FAILURE" ] && final_report
    elif grep "Bailing out" "$CMD_OUTPUT" ; then
        echo -en "\nExit status: 0, but bail-out detected (FAIL)\n" >> "$FINAL_REPORT"
        [ "$STOP_ON_FAILURE" ] && final_report
    else
        echo -en "\nExit status: 0 (PASS)\n" >> "$FINAL_REPORT"
    fi
}

function test_tunnel {
    local dep_id="$1"
    local service="$2"
    local protocol="$3"
    local port="$4"
    local search_string="$5"
    local exit_status
    [ -z "$service" ]       && service="dashboard"
    [ -z "$protocol" ]      && protocol="https"
    [ -z "$port" ]          && port="8443"
    [ -z "$search_string" ] && search_string="SUSE Enterprise Storage"
    timeout 40s sesdev tunnel "$dep_id" "$service" &
    sleep 30
    true > "$TEMP_FILE"
    curl --silent --insecure "$protocol://127.0.0.1:$port" | tee "$TEMP_FILE"
    grep "$search_string" "$TEMP_FILE"
    exit_status="$?"
    sleep 15
    return "$exit_status"
}

function tunnel_gone {
    local protocol="$1"
    local port="$2"
    local curl_output
    [ -z "$protocol" ] && protocol="https"
    [ -z "$port" ]     && port="8443"
    curl_output="$(curl --silent --insecure "$protocol://127.0.0.1:$port")"
    if [ "$curl_output" ] ; then
        echo "ERROR: tunnel is unexpectedly still there - bailing out!"
        return 1
    else
        return 0
    fi
}

GETOPT=$(getopt -o h \
--long "help,caasp4,ceph-salt-branch:,ceph-salt-repo:,full,makecheck,nautilus,no-stop-on-failure,octopus,pacific,ses6,ses7" \
-n 'standalone.sh' -- "$@")
set +e
eval set -- "$GETOPT"

# process command-line options
NORMAL_OPERATION="not_empty"
CAASP4=""
CEPH_SALT_OPTIONS=()
CEPH_SALT_BRANCH=""
CEPH_SALT_REPO=""
FULL=""
MAKECHECK=""
NAUTILUS=""
OCTOPUS=""
PACIFIC=""
SES6=""
SES7=""
STOP_ON_FAILURE="not_empty"
while true ; do
    case "$1" in
        --caasp4)                CAASP4="--caasp4" ; shift ;;
        --ceph-salt-branch) shift; CEPH_SALT_BRANCH="$1" ; shift ;;
        --ceph-salt-repo) shift; CEPH_SALT_REPO="$1" ; shift ;;
        --full)                  FULL="$1" ; shift ;;
        --makecheck)             MAKECHECK="$1" ; shift ;;
        --nautilus)              NAUTILUS="$1" ; shift ;;
        --no-stop-on-failure)    STOP_ON_FAILURE="" ; shift ;;
        --octopus)               OCTOPUS="$1" ; shift ;;
        --pacific)               PACIFIC="$1" ; shift ;;
        --ses6)                  SES6="$1" ; shift ;;
        --ses7)                  SES7="$1" ; shift ;;
        -h|--help)               usage ; exit 0 ;;
        --) shift ; break ;;
        *) echo "Internal error" ; exit 1 ;;
    esac
done

if [ "$*" ] ; then
    usage
    echo "ERROR: unrecognized parameters \"$*\""
    exit 1
fi

if [ "$CAASP4" ] || [ "$FULL" ] || [ "$MAKECHECK" ] || [ "$NAUTILUS" ] || [ "$OCTOPUS" ] || [ "$PACIFIC" ] || [ "$SES6" ] || [ "$SES7" ] ; then
    NORMAL_OPERATION=""
fi

if [ "$FULL" ] || [ "$NORMAL_OPERATION" ] ; then
    if [ "$FULL" ] ; then
        CAASP4="--caasp4"
        MAKECHECK="--makecheck"
    fi
    NAUTILUS="--nautilus"
    OCTOPUS="--octopus"
    PACIFIC="--pacific"
    SES6="--ses6"
    SES7="--ses7"
fi

if [ "$CEPH_SALT_BRANCH" ] || [ "$CEPH_SALT_REPO" ] ; then
    if [ "$CEPH_SALT_REPO" ] ; then
        if [[ "$CEPH_SALT_REPO" =~ ^[_[:alnum:]]+$ ]] ; then
            CEPH_SALT_REPO="https://github.com/$CEPH_SALT_REPO/ceph-salt"
        fi
    else
        CEPH_SALT_REPO="https://github.com/ceph/ceph-salt"
    fi
    CEPH_SALT_OPTIONS+=( "--ceph-salt-repo" "$CEPH_SALT_REPO" )
    if [ "$CEPH_SALT_BRANCH" ] ; then
        true
    else
        CEPH_SALT_BRANCH="master"
    fi
    CEPH_SALT_OPTIONS+=( "--ceph-salt-branch" "$CEPH_SALT_BRANCH" )
fi

if [ "$(sesdev status --format json | jq -r '. | length')" != "0" ] ; then
     echo "ERROR: detected existing deployments"
     echo "(This script expects a clean environment -- i.e., \"sesdev status\" must be empty)"
     exit 1
fi

if [ -f "$CONFIG_YAML" ] || [ ! -s "$CONFIG_YAML" ] ; then
    rm -f "$CONFIG_YAML"
fi

if [ -e "$CONFIG_YAML" ] ; then
    echo "ERROR: detected possibly non-empty $CONFIG_YAML"
    echo "(The existence of this file can skew the test results!)"
    exit 1
fi

set -x
touch "$CONFIG_YAML"

if [ "$NAUTILUS" ] ; then
    sesdev --verbose box remove --non-interactive leap-15.1
    # dry run
    run_cmd sesdev create nautilus --dry-run
    run_cmd sesdev --verbose create nautilus --non-interactive --single-node --filestore nautilus-1node
    run_cmd sesdev --verbose qa-test nautilus-1node
    run_cmd sesdev --verbose destroy --non-interactive nautilus-1node
    run_cmd sesdev --verbose create nautilus --non-interactive nautilus-4node
    run_cmd sesdev --verbose qa-test nautilus-4node
    run_cmd sesdev --verbose destroy --non-interactive nautilus-4node
fi

if [ "$SES6" ] ; then
    sesdev --verbose box remove --non-interactive sles-15-sp1
    # dry run
    run_cmd sesdev create ses6 --dry-run
    run_cmd sesdev --verbose create ses6 --non-interactive --roles "[master,storage,mon,mgr]" ses6-mini
    run_cmd sesdev --verbose qa-test ses6-mini
    run_cmd sesdev --verbose destroy --non-interactive ses6-mini
    run_cmd sesdev --verbose create ses6 --product --non-interactive --single-node ses6-1node
    run_cmd sesdev --verbose qa-test ses6-1node
    run_cmd sesdev --verbose add-repo --update ses6-1node
    run_cmd sesdev --verbose destroy --non-interactive ses6-1node
    run_cmd sesdev --verbose create ses6 --non-interactive --fqdn ses6-4node
    run_cmd sesdev --verbose qa-test ses6-4node
    run_cmd sesdev --verbose supportconfig ses6-4node node1
    rm -f scc*
    # consider uncommenting after the following bugs are fixed:
    # - https://github.com/SUSE/sesdev/issues/276
    # - https://github.com/SUSE/sesdev/issues/291
    # run_cmd test_tunnel ses6-4node
    # run_cmd tunnel_gone
    run_cmd sesdev --verbose destroy --non-interactive ses6-4node
fi

if [ "$OCTOPUS" ] ; then
    sesdev --verbose box remove --non-interactive leap-15.2
    # dry run
    run_cmd sesdev create octopus --dry-run
    run_cmd sesdev --verbose create octopus --non-interactive "${CEPH_SALT_OPTIONS[@]}" --single-node octopus-1node
    run_cmd sesdev --verbose qa-test octopus-1node
    run_cmd sesdev --verbose destroy --non-interactive octopus-1node
    run_cmd sesdev --verbose create octopus --non-interactive "${CEPH_SALT_OPTIONS[@]}" --fqdn octopus-4node
    run_cmd sesdev --verbose qa-test octopus-4node
    run_cmd sesdev status octopus-4node
    run_cmd sesdev --verbose destroy --non-interactive octopus-4node
    run_cmd expect_fail sesdev status octopus-4node
fi

if [ "$SES7" ] ; then
    sesdev --verbose box remove --non-interactive sles-15-sp2
    # dry run
    run_cmd sesdev create ses7 --dry-run
    run_cmd sesdev --verbose create ses7 --non-interactive --roles "[admin,master,bootstrap,storage,mon,mgr]" ses7-mini
    run_cmd sesdev --verbose show ses7-mini
    run_cmd sesdev --verbose show --detail ses7-mini
    run_cmd test "$(sesdev show ses7-mini --format json --nodes-with-role bootstrap | jq -r '.[0]')" = "master"
    run_cmd sesdev --verbose qa-test ses7-mini
    run_cmd sesdev --verbose destroy --non-interactive ses7-mini
    run_cmd sesdev --verbose create ses7 --non-interactive "${CEPH_SALT_OPTIONS[@]}" --single-node --fqdn ses7-1node-fqdn
    run_cmd sesdev --verbose qa-test ses7-1node-fqdn
    run_cmd sesdev --verbose destroy --non-interactive ses7-1node-fqdn
    run_cmd sesdev --verbose create ses7 --non-interactive "${CEPH_SALT_OPTIONS[@]}" --single-node --product ses7-1node-product
    run_cmd sesdev --verbose qa-test ses7-1node-product
    run_cmd sesdev --verbose destroy --non-interactive ses7-1node-product
    run_cmd sesdev --verbose create ses7 --non-interactive "${CEPH_SALT_OPTIONS[@]}" ses7-4node
    run_cmd sesdev --verbose qa-test ses7-4node
    run_cmd sesdev --verbose supportconfig ses7-4node node1
    rm -f scc*
    # consider uncommenting after the following bugs are fixed:
    # - bsc#1170498
    # - https://github.com/SUSE/sesdev/issues/276
    # - https://github.com/SUSE/sesdev/issues/291
    # run_cmd test_tunnel ses7-4node
    # run_cmd tunnel_gone
    run_cmd sesdev --verbose destroy --non-interactive ses7-4node
fi

if [ "$PACIFIC" ] ; then
    sesdev --verbose box remove --non-interactive leap-15.3
    # dry run
    run_cmd sesdev create pacific --dry-run
    run_cmd sesdev --verbose create pacific --non-interactive "${CEPH_SALT_OPTIONS[@]}" --single-node pacific-1node
    run_cmd sesdev --verbose qa-test pacific-1node
    run_cmd sesdev --verbose destroy --non-interactive pacific-1node
    run_cmd sesdev --verbose create pacific --non-interactive "${CEPH_SALT_OPTIONS[@]}" --single-node --ipv6 pacific-1node-ipv6
    run_cmd sesdev --verbose qa-test pacific-1node-ipv6
    run_cmd sesdev --verbose destroy --non-interactive pacific-1node-ipv6
    run_cmd sesdev --verbose create pacific --non-interactive "${CEPH_SALT_OPTIONS[@]}" --fqdn pacific-4node
    run_cmd sesdev --verbose qa-test pacific-4node
    run_cmd sesdev --verbose destroy --non-interactive pacific-4node
fi

if [ "$MAKECHECK" ] ; then
    sesdev --verbose box remove --non-interactive tumbleweed
    # dry run
    run_cmd sesdev create makecheck --dry-run
    run_cmd sesdev --verbose create makecheck --non-interactive --stop-before-run-make-check --ram 4
    run_cmd sesdev --verbose destroy --non-interactive makecheck-tumbleweed
    run_cmd sesdev --verbose create makecheck --non-interactive --os sles-15-sp1 --stop-before-run-make-check --ram 4
    run_cmd sesdev --verbose destroy --non-interactive makecheck-sles-15-sp1
    run_cmd sesdev --verbose create makecheck --non-interactive --os sles-15-sp2 --stop-before-run-make-check --ram 4
    run_cmd sesdev status makecheck-sles-15-sp2
    run_cmd sesdev --verbose destroy --non-interactive makecheck-sles-15-sp2
    run_cmd expect_fail sesdev status makecheck-sles-15-sp2
fi

if [ "$CAASP4" ] ; then
    # dry run
    run_cmd sesdev create caasp4 --dry-run
    run_cmd sesdev --verbose create caasp4 --non-interactive caasp4-default
    run_cmd sesdev --verbose destroy --non-interactive caasp4-default
    run_cmd sesdev --verbose create caasp4 --non-interactive --deploy-ses caasp4-with-rook
    run_cmd sesdev --verbose destroy --non-interactive caasp4-with-rook
    run_cmd sesdev --verbose create caasp4 --non-interactive --single-node --deploy-ses
    run_cmd sesdev --verbose destroy --non-interactive caasp4-mini
fi

if [ "$(sesdev status --format json | jq -r '. | length')" != "0" ] ; then
    echo "ERROR: dangling deployments detected"
    echo "(One or more deployments created by this script were not destroyed)"
    exit 1
fi

final_report
