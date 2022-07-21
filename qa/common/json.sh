#!/bin/bash
#
# This file is part of the sesdev-qa integration test suite.
# It contains various cluster introspection functions.
#

set -e

function json_ses7_orch_ls {
    # returns number of deployed services of a given type, according to "ceph orch ls"
    if [ "$VERSION_ID" = "15.2" ] || [ "$VERSION_ID" = "15.3" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local service_type="$1"
        local ceph_orch_ls
        local running
        ceph_orch_ls="$(ceph orch ls --service-type "$service_type" --format json)"
        if echo "$ceph_orch_ls" | jq -r >/dev/null 2>&1 ; then
            running="$(echo "$ceph_orch_ls" | jq -r '.[] | .status.running')"
            echo "$running"
        else
            echo "0"
        fi
    else
        echo "ERROR"
    fi
}

function json_ses7_orch_ps {
    # returns number of running daemons of a given type, according to "ceph orch ps"
    if [ "$VERSION_ID" = "15.2" ] || [ "$VERSION_ID" = "15.3" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local daemon_type="$1"
        local ceph_orch_ps
        local running
        ceph_orch_ps="$(ceph orch ps --daemon-type "$daemon_type" -f json-pretty)"
        if echo "$ceph_orch_ps" | jq -r >/dev/null 2>&1 ; then
            running="$(echo "$ceph_orch_ps" | jq -r '[ .[] | select(.status_desc == "running") ] | length')"
            echo "$running"
        else
            echo "0"
        fi
    else
        echo "ERROR"
    fi
}

function json_total_nodes {
    salt --static --out json '*' test.ping 2>/dev/null | jq '. | length'
}

function json_osd_nodes {
    ceph osd tree -f json-pretty | \
        jq '[.nodes[] | select(.type == "host")] | length'
}

function json_mgr_is_available {
    if [ "$(ceph status --format json | jq -r .mgrmap.available)" = "true" ] ; then
        echo "not_the_empty_string"
    else
        echo ""
    fi
}

function json_metadata_mgrs {
    ceph mgr metadata | jq -r '. | length'
}

function json_total_mgrs {
    local ceph_status_json
    local active_mgrs
    if [ "$VERSION_ID" = "15.2" ] || [ "$VERSION_ID" = "15.3" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        json_ses7_orch_ls mgr
    elif [ "$VERSION_ID" = "15.1" ] ; then
        # SES6
        ceph_status_json="$(ceph status --format json)"
        if [ "$(echo "$ceph_status_json" | jq -r .mgrmap.available)" = "true" ] ; then
            active_mgrs="1"
        else
            active_mgrs="0"
        fi
        echo "$(($(echo "$ceph_status_json" | jq -r ".mgrmap.standbys | length") + active_mgrs))"
    else
        echo "ERROR"
    fi
}

function json_metadata_mons {
    ceph mon metadata | jq -r '. | length'
}

function json_total_mons {
    local ceph_status_json
    if [ "$VERSION_ID" = "15.2" ] || [ "$VERSION_ID" = "15.3" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        json_ses7_orch_ls mon
    elif [ "$VERSION_ID" = "15.1" ] ; then
        # SES6
        ceph_status_json="$(ceph status --format json)"
        echo "$ceph_status_json" | jq -r ".monmap.num_mons"
    else
        echo "ERROR"
    fi
}

function json_metadata_mdss {
    ceph mds metadata | jq -r '. | length'
}

function json_total_mdss {
    local ceph_status_json
    local ins
    local ups
    local standbys
    local actives
    if [ "$VERSION_ID" = "15.2" ] || [ "$VERSION_ID" = "15.3" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        json_ses7_orch_ls mds
    elif [ "$VERSION_ID" = "15.1" ] ; then
        # SES6
        ceph_status_json="$(ceph status --format json)"
        ins="$(echo "$ceph_status_json" | jq -r .fsmap.in)"
        ups="$(echo "$ceph_status_json" | jq -r .fsmap.up)"
        standbys="$(echo "$ceph_status_json" | jq -r '."fsmap"."up:standby"')"
        if [ "$ins" = "$ups" ] ; then
            actives="$ins"
        else
            actives="0"
        fi
        echo "$((actives + standbys))"
    else
        echo "ERROR"
    fi
}

function json_total_rgws {
    ceph status -f json-pretty | jq '.servicemap.services.rgw.daemons | del(.summary) | length'
}

function json_metadata_osds {
    ceph osd metadata | jq -r '. | length'
}

function json_total_osds {
    ceph osd ls --format json | jq '. | length'
}
