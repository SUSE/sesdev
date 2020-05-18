#!/bin/bash
#
# This file is part of the sesdev-qa integration test suite.
# It contains various cluster introspection functions.
#

set -e

function _json_total_svcs_ses7 {
    local svc_type="$1"
    local ceph_orch_ls
    local running
    ceph_orch_ls="$(ceph orch ls --service-type "$svc_type" --format json)"
    running="$(echo "$ceph_orch_ls" | jq -r '.[] | .running')"
    if [ "$running" = "null" ] ; then
        # we have fallen victim to ongoing Orchestrator refactoring
        running="$(echo "$ceph_orch_ls" | jq -r '.[] | .status.running')"
    fi
    echo "$running"
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
    ceph_status_json="$(ceph status --format json)"
    local active_mgrs
    if [ "$VERSION_ID" = "15.2" ] ; then
        # SES7
        _json_total_svcs_ses7 mgr
    elif [ "$VERSION_ID" = "15.1" ] || [ "$VERSION_ID" = "12.3" ] ; then
        # SES6, SES5
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
    if [ "$VERSION_ID" = "15.2" ] ; then
        # SES7
        _json_total_svcs_ses7 mon
    elif [ "$VERSION_ID" = "15.1" ] || [ "$VERSION_ID" = "12.3" ] ; then
        # SES6, SES5
        ceph status --format json | jq -r ".monmap.mons | length"
    else
        echo "ERROR"
    fi
}

function json_metadata_mdss {
    ceph mds metadata | jq -r '. | length'
}

function json_total_mdss {
    local ceph_status_json
    ceph_status_json="$(ceph status --format json)"
    local ins
    local ups
    local standbys
    local actives
    if [ "$VERSION_ID" = "15.2" ] ; then
        # SES7
        _json_total_svcs_ses7 mds
    elif [ "$VERSION_ID" = "15.1" ] || [ "$VERSION_ID" = "12.3" ] ; then
        # SES6, SES5
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

function json_metadata_rgws {
    ceph orch ps -f json-pretty | jq '[.[] | select(.daemon_type=="rgw" and .status_desc=="running")] | length'
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
