#!/bin/bash
# This file is part of the sesdev-qa integration test suite

set -e

#
# helper functions (not to be called directly from test scripts)
#

function _ceph_cluster_running {
    set -x
    ceph status
    set +x
}

function _copy_file_from_minion_to_master {
    local MINION="$1"
    local FULL_PATH="$2"
    salt --static --out json "$MINION" cmd.shell "cat $FULL_PATH" | jq -r \.\""$MINION"\" > "$FULL_PATH"
}

function _first_x_node {
    local role=$1
    if [ "$role" = "igw" ] ; then
        echo "${IGW_NODE_LIST%%,*}"
    elif [ "$role" = "bootstrap" ] ; then
        echo "${BOOTSTRAP_NODE}"
    elif [ "$role" = "mds" ] ; then
        echo "${MDS_NODE_LIST%%,*}"
    elif [ "$role" = "mgr" ] ; then
        echo "${MGR_NODE_LIST%%,*}"
    elif [ "$role" = "mon" ] ; then
        echo "${MON_NODE_LIST%%,*}"
    elif [ "$role" = "nfs" ] ; then
        echo "${NFS_NODE_LIST%%,*}"
    elif [ "$role" = "osd" ] ; then
        echo "${OSD_NODE_LIST%%,*}"
    elif [ "$role" = "rgw" ] ; then
        echo "${RGW_NODE_LIST%%,*}"
    else
        echo ""
    fi
}

function _grace_period {
    local SECONDS
    SECONDS="$1"
    local counter
    counter="$2"
    if [ "$counter" ] ; then
        echo "${SECONDS}-second grace period ($counter)"
    else
        echo "${SECONDS}-second grace period"
    fi
    sleep "$SECONDS"
}

function _ping_minions_until_all_respond {
    local RESPONDING
    for i in {1..20} ; do
        _grace_period 10 "$i"
        RESPONDING=$(salt '*' test.ping 2>/dev/null | grep --count True 2>/dev/null)
        echo "Of $TOTAL_NODES total minions, $RESPONDING are responding"
        test "$TOTAL_NODES" -eq "$RESPONDING" && break
    done
}

function _extract_ceph_version {
    # given a command that outputs a string like this:
    #
    #     ceph version 15.1.0-1521-gcdf35413a0 (cdf35413a036bd1aa59a8c718bb177839c45cab1) octopus (rc)
    #
    # return just the part before the first parentheses
    local full_version_string="$1"
    # shellcheck disable=SC2003
    expr match "$full_version_string" '\(ceph version [^[:space:]]\+\)'
}

function _fsid {
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        ceph status --format=json | jq -r '.fsid'
    else
        echo "ERROR: _fsid needs Octopus or newer"
        false
    fi
}

function _osd_objectstore {
    # sample output for a cluster with 4 FileStore OSDs:
    # filestore 
    # filestore 
    # filestore 
    # filestore 
    ceph osd metadata | jq -r '.[] | .osd_objectstore'
}
