#
# This file is part of the sesdev-qa integration test suite.
# It contains various cluster introspection functions.
#

set -e

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

function json_total_mgrs {
    #
    # I have not found any straightforward way of obtaining the number of
    # running MGRs from the "ceph status --format json" output. What I'm
    # doing is:
    #
    # (1) if the mgrmap has "available: true" then "number of active MGRs"
    #     is 1, otherwise 0
    #
    # (2) obtain the number of standby MGRs by consulting the mgrmap
    #
    # (3) total number of MGRs = number of active MGRs + number of standby MGRs
    #
    local ceph_status_json="$(ceph status --format json)"
    local active_mgrs=""
    if [ "$(echo "$ceph_status_json" | jq -r .mgrmap.available)" = "true" ] ; then
        active_mgrs="1"
    else
        active_mgrs="0"
    fi
    if [ "$VERSION_ID" = "15.2" ] ; then
        # SES7
        echo "$(("$(echo "$ceph_status_json" | jq -r .mgrmap.num_standbys)" + "$active_mgrs"))"
    elif [ "$VERSION_ID" = "15.1" ] ; then
        # SES6
        echo "$(("$(echo "$ceph_status_json" | jq -r ".mgrmap.standbys | length")" + "$active_mgrs"))"
    elif [ "$VERSION_ID" = "12.3" ] ; then
        # SES5
        echo "$(("$(echo "$ceph_status_json" | jq -r ".mgrmap.standbys | length")" + "$active_mgrs"))"
    else
        echo "0"
    fi
}

function json_total_mons {
    if [ "$VERSION_ID" = "15.2" ] ; then
        # SES7
        echo "$(ceph status --format json | jq -r .monmap.num_mons)"
    elif [ "$VERSION_ID" = "15.1" ] ; then
        # SES6
        echo "$(ceph status --format json | jq -r ".monmap.mons | length")"
    elif [ "$VERSION_ID" = "12.3" ] ; then
        # SES5
        echo "$(ceph status --format json | jq -r ".monmap.mons | length")"
    else
        echo "0"
    fi
}

function json_total_osds {
    ceph osd ls --format json | jq '. | length'
}
