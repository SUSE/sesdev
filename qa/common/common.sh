#!/bin/bash
#
# This file is part of the sesdev-qa integration test suite
#

set -e

# BASEDIR is set by the calling script
# shellcheck disable=SC1090
# shellcheck disable=SC1091
source "$BASEDIR/common/helper.sh"
# shellcheck disable=SC1090
# shellcheck disable=SC1091
source "$BASEDIR/common/json.sh"
# shellcheck disable=SC1090
# shellcheck disable=SC1091
source "$BASEDIR/common/zypper.sh"


#
# functions that process command-line arguments
#

function assert_enhanced_getopt {
    set +e
    echo -n "Running 'getopt --test'... "
    getopt --test > /dev/null
    if [ $? -ne 4 ]; then
        echo "FAIL"
        echo "This script requires enhanced getopt. Bailing out."
        exit 1
    fi
    echo "PASS"
    set -e
}


#
# functions that print status information
#

function cat_salt_config {
    cat /etc/salt/master
    cat /etc/salt/minion
}

function salt_pillar_items {
    salt '*' pillar.items
}

function salt_pillar_get_roles {
    salt '*' pillar.get roles
}

function salt_cmd_run_lsblk {
    salt '*' cmd.run lsblk
}

function cat_ceph_conf {
    salt '*' cmd.run "cat /etc/ceph/ceph.conf" 2>/dev/null
}

function admin_auth_status {
    ceph auth get client.admin
    ls -l /etc/ceph/ceph.client.admin.keyring
    cat /etc/ceph/ceph.client.admin.keyring
}

function number_of_hosts_in_ceph_osd_tree {
    ceph osd tree -f json-pretty | jq '[.nodes[] | select(.type == "host")] | length'
}

function number_of_osds_in_ceph_osd_tree {
    ceph osd tree -f json-pretty | jq '[.nodes[] | select(.type == "osd")] | length'
}

function ceph_cluster_status {
    ceph pg stat -f json-pretty
    _grace_period 1
    ceph health detail -f json-pretty
    _grace_period 1
    ceph osd tree
    _grace_period 1
    ceph osd pool ls detail -f json-pretty
    _grace_period 1
    ceph -s
}

function ceph_log_grep_enoent_eaccess {
    set +e
    grep -rH "Permission denied" /var/log/ceph
    grep -rH "No such file or directory" /var/log/ceph
    set -e
}


#
# core validation tests
#

function support_cop_out_test {
    set +x
    local supported
    supported="sesdev-qa supports this OS"
    local not_supported
    not_supported="ERROR: sesdev-qa does not currently support this OS"
    echo
    echo "WWWW: ceph_version_test"
    echo "Detected operating system $NAME $VERSION_ID"
    case "$ID" in
        opensuse*|suse|sles)
            case "$VERSION_ID" in
                15*)
                    echo "$supported"
                    ;;
                *)
                    echo "$not_supported"
                    ;;
            esac
            ;;
        *)
            echo "$not_supported"
            false
            ;;
    esac
    set +x
    echo "support_cop_out_test: OK"
    echo
}

function make_salt_master_an_admin_node_test {
    local arbitrary_mon_node
    echo
    echo "WWWW: make_salt_master_an_admin_node_test"
    _zypper_install_on_master ceph-common
    mkdir -p "/etc/ceph"
    if [ -f "$ADMIN_KEYRING" ] || [ -f "$CEPH_CONF" ] ; then
        true
    else
        set -x
        arbitrary_mon_node="$(_first_x_node mon)"
        if [ ! -f "$ADMIN_KEYRING" ] ; then
            _copy_file_from_minion_to_master "$arbitrary_mon_node" "$ADMIN_KEYRING"
            chmod 0600 "$ADMIN_KEYRING"
        fi
        if [ ! -f "$CEPH_CONF" ] ; then
            _copy_file_from_minion_to_master "$arbitrary_mon_node" "$CEPH_CONF"
        fi
        set +x
    fi
    set -x
    test -f "$ADMIN_KEYRING"
    test -f "$CEPH_CONF"
    set +x
    echo "make_salt_master_an_admin_node_test: OK"
    echo
}

function ceph_rpm_version_test {
# test that ceph RPM version matches "ceph --version"
# for a loose definition of "matches"
    echo
    echo "WWWW: ceph_rpm_version_test"
    set -x
    rpm -q ceph-common
    set +x
    local rpm_name
    rpm_name="$(rpm -q ceph-common)"
    local rpm_ceph_version
    rpm_ceph_version="$(perl -e '"'"$rpm_name"'" =~ m/ceph-common-(\d+\.\d+\.\d+)/; print "$1\n";')"
    echo "According to RPM, the ceph upstream version is ->$rpm_ceph_version<-"
    test -n "$rpm_ceph_version"
    set -x
    ceph --version
    set +x
    local buffer
    buffer="$(ceph --version)"
    local ceph_ceph_version
    ceph_ceph_version="$(perl -e '"'"$buffer"'" =~ m/ceph version (\d+\.\d+\.\d+)/; print "$1\n";')"
    echo "According to \"ceph --version\", the ceph upstream version is ->$ceph_ceph_version<-"
    test -n "$rpm_ceph_version"
    set -x
    test "$rpm_ceph_version" = "$ceph_ceph_version"
    set +x
    echo "ceph_rpm_version_test: OK"
    echo
}

function ceph_daemon_versions_test {
    local strict_versions="$1"
    local version_host
    local version_daemon
    echo
    echo "WWWW: ceph_daemon_versions_test"
    set -x
    ceph --version
    ceph versions
    set +x
    version_host="$(_extract_ceph_version "$(ceph --version)")"
    version_daemon="$(_extract_ceph_version "$(ceph versions | jq -r '.overall | keys[]')")"
    if [ "$strict_versions" ] ; then
        set -x
        test "$version_host" = "$version_daemon"
    fi
    set +x
    echo "ceph_daemon_versions_test: OK"
    echo
}

function ceph_cluster_running_test {
    echo
    echo "WWWW: ceph_cluster_running_test"
    _ceph_cluster_running
    echo "ceph_cluster_running_test: OK"
    echo
}

function ceph_health_test {
# wait for up to some minutes for cluster to reach HEALTH_OK
    echo
    echo "WWWW: ceph_health_test"
    local minutes_to_wait
    minutes_to_wait="5"
    local cluster_status
    local minute
    local i
    for minute in $(seq 1 "$minutes_to_wait") ; do
        for i in $(seq 1 4) ; do
            set -x
            ceph status
            cluster_status="$(ceph health detail --format json | jq -r .status)"
            set +x
            if [ "$cluster_status" = "HEALTH_OK" ] ; then
                break 2
            else
                _grace_period 15 "$i"
            fi
        done
        echo "Minutes left to wait: $((minutes_to_wait - minute))"
    done
    if [ "$cluster_status" = "HEALTH_OK" ] ; then
        echo "ceph_health_test: OK"
        echo
    else
        echo "HEALTH_OK not reached even after waiting for $minutes_to_wait minutes"
        echo "ceph_health_test: FAIL"
        echo
        false
    fi
}

function maybe_wait_for_osd_nodes_test {
    local expected_osd_nodes="$1"
    local actual_osd_nodes
    local minutes_to_wait
    minutes_to_wait="5"
    local minute
    local i
    local success
    echo
    echo "WWWW: maybe_wait_for_osd_nodes_test"
    if [ "$expected_osd_nodes" ] ; then
        echo "Waiting up to $minutes_to_wait minutes for all $expected_osd_nodes OSD node(s) to show up..."
        for minute in $(seq 1 "$minutes_to_wait") ; do
            for i in $(seq 1 4) ; do
                set -x
                actual_osd_nodes="$(json_osd_nodes)"
                set +x
                if [ "$actual_osd_nodes" = "$expected_osd_nodes" ] ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
    else
        success="not_empty"
        echo "No OSD nodes expected: nothing to wait for."
    fi
    if [ "$success" ] ; then
        echo "maybe_wait_for_osd_nodes_test: OK"
        echo
    else
        echo "maybe_wait_for_osd_nodes_test: FAIL"
        false
    fi
}

function maybe_wait_for_mdss_test {
    local expected_mdss="$1"
    local actual_mdss
    local minutes_to_wait
    minutes_to_wait="5"
    local metadata_mdss
    local minute
    local i
    local success
    echo
    echo "WWWW: maybe_wait_for_mdss_test"
    if [ "$expected_mdss" ] ; then
        echo "Waiting up to $minutes_to_wait minutes for all $expected_mdss MDS(s) to show up..."
        for minute in $(seq 1 "$minutes_to_wait") ; do
            for i in $(seq 1 4) ; do
                set -x
                metadata_mdss="$(json_metadata_mdss)"
                actual_mdss="$(json_total_mdss)"
                set +x
                if [ "$actual_mdss" = "$expected_mdss" ] && [ "$actual_mdss" = "$metadata_mdss" ] ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
    else
        success="not_empty"
        echo "No MDSs expected: nothing to wait for."
    fi
    if [ "$success" ] ; then
        echo "maybe_wait_for_mdss_test: OK"
        echo
    else
        echo "maybe_wait_for_mdss_test: FAIL"
        echo
        false
    fi
}

function mgr_is_available_test {
    echo
    echo "WWWW: mgr_is_available_test"
    test "$(json_mgr_is_available)"
    echo "mgr_is_available_test: OK"
    echo
}

function number_of_daemons_expected_vs_metadata_test {
    echo
    echo "WWWW: number_of_daemons_expected_vs_metadata_test"
    set -x
    local metadata_mgrs
    metadata_mgrs="$(json_metadata_mgrs)"
    local metadata_mons
    metadata_mons="$(json_metadata_mons)"
    local metadata_mdss
    metadata_mdss="$(json_metadata_mdss)"
    local metadata_osds
    metadata_osds="$(json_metadata_osds)"
    set +x
    local success
    success="yes"
    local expected_mgrs
    local expected_mons
    local expected_mdss
    local expected_osds
    [ "$MGR_NODES" ] && expected_mgrs="$MGR_NODES"
    [ "$MON_NODES" ] && expected_mons="$MON_NODES"
    [ "$MDS_NODES" ] && expected_mdss="$MDS_NODES"
    [ "$OSDS" ]      && expected_osds="$OSDS"
    if [ "$expected_mons" ] ; then
        echo "MONs metadata/expected: $metadata_mons/$expected_mons"
        [ "$metadata_mons" = "$expected_mons" ] || success=""
    fi
    if [ "$expected_mgrs" ] ; then
        echo "MGRs metadata/expected: $metadata_mgrs/$expected_mgrs"
        [ "$metadata_mgrs" = "$expected_mgrs" ] || success=""
    fi
    if [ "$expected_mdss" ] ; then
        echo "MDSs metadata/expected: $metadata_mdss/$expected_mdss"
        [ "$metadata_mdss" = "$expected_mdss" ] || success=""
    fi
    if [ "$expected_osds" ] ; then
        echo "OSDs metadata/expected: $metadata_osds/$expected_osds"
        [ "$metadata_osds" = "$expected_osds" ] || success=""
    fi
    if [ "$success" ] ; then
        echo "number_of_daemons_expected_vs_metadata_test: OK"
        echo
    else
        echo "ERROR: Detected disparity between expected number of daemons and cluster metadata!"
        echo "number_of_daemons_expected_vs_metadata_test: FAIL"
        echo
        false
    fi
}

function number_of_nodes_actual_vs_expected_test {
    echo
    echo "WWWW: number_of_nodes_actual_vs_expected_test"
    set -x
    local actual_total_nodes
    actual_total_nodes="$(json_total_nodes)"
    local actual_mgr_nodes
    actual_mgr_nodes="$(json_total_mgrs)"
    local actual_mon_nodes
    actual_mon_nodes="$(json_total_mons)"
    local actual_mds_nodes
    actual_mds_nodes="$(json_total_mdss)"
    local actual_osd_nodes
    actual_osd_nodes="$(json_osd_nodes)"
    local actual_osds
    actual_osds="$(json_total_osds)"
    set +x
    local success
    success="yes"
    local expected_total_nodes
    local expected_mgr_nodes
    local expected_mon_nodes
    local expected_mds_nodes
    local expected_osd_nodes
    local expected_osds
    [ "$TOTAL_NODES" ] && expected_total_nodes="$TOTAL_NODES"
    [ "$MGR_NODES" ]   && expected_mgr_nodes="$MGR_NODES"
    [ "$MON_NODES" ]   && expected_mon_nodes="$MON_NODES"
    [ "$MDS_NODES" ]   && expected_mds_nodes="$MDS_NODES"
    [ "$OSD_NODES" ]   && expected_osd_nodes="$OSD_NODES"
    [ "$OSDS" ]        && expected_osds="$OSDS"
    if [ "$expected_total_nodes" ] ; then
        echo "total nodes actual/expected:  $actual_total_nodes/$expected_total_nodes"
        [ "$actual_total_nodes" = "$expected_total_nodes" ] || success=""
    fi
    if [ "$expected_mon_nodes" ] ; then
        echo "MON nodes actual/expected:    $actual_mon_nodes/$expected_mon_nodes"
        [ "$actual_mon_nodes" = "$expected_mon_nodes" ] || success=""
    fi
    if [ "$expected_mgr_nodes" ] ; then
        echo "MGR nodes actual/expected:    $actual_mgr_nodes/$expected_mgr_nodes"
        [ "$actual_mgr_nodes" = "$expected_mgr_nodes" ] || success=""
    fi
    if [ "$expected_mds_nodes" ] ; then
        echo "MDS nodes actual/expected:    $actual_mds_nodes/$expected_mds_nodes"
        [ "$actual_mds_nodes" = "$expected_mds_nodes" ] || success=""
    fi
    if [ "$expected_osd_nodes" ] ; then
        echo "OSD nodes actual/expected:    $actual_osd_nodes/$expected_osd_nodes"
        [ "$actual_osd_nodes" = "$expected_osd_nodes" ] || success=""
    fi
    if [ "$expected_osds" ] ; then
        echo "total OSDs actual/expected:   $actual_osds/$expected_osds"
        [ "$actual_osds" = "$expected_osds" ] || success=""
    fi
#    echo "RGW nodes expected:     $RGW_NODES"
#    echo "IGW nodes expected:     $IGW_NODES"
#    echo "NFS nodes expected:     $NFS_NODES"
    if [ "$success" ] ; then
        echo "number_of_nodes_actual_vs_expected_test: OK"
        echo
    else
        echo "ERROR: Detected disparity between expected and actual numbers of nodes/daemons"
        echo "number_of_nodes_actual_vs_expected_test: FAIL"
        echo
        false
    fi
}
