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

function json_total_mgrs {
    if [ "$VERSION_ID" = "15.2" ] ; then
        # SES7
        echo "$(($(ceph status --format json | jq -r .mgrmap.num_standbys) + 1))"
    elif [ "$VERSION_ID" = "15.1" ] ; then
        # SES6
        echo "$(($(ceph status --format json | jq -r ".mgrmap.standbys | length") + 1))"
    elif [ "$VERSION_ID" = "12.3" ] ; then
        # SES5
        echo "$(($(ceph status --format json | jq -r ".mgrmap.standbys | length") + 1))"
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
