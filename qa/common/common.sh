#
# This file is part of the sesdev-qa integration test suite
#

set -e

# BASEDIR is set by the calling script
source $BASEDIR/common/helper.sh
source $BASEDIR/common/json.sh
source $BASEDIR/common/zypper.sh


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
    local supported="sesdev-qa supports this OS"
    local not_supported="ERROR: sesdev-qa does not currently support this OS"
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

function ceph_rpm_version_test {
# test that ceph RPM version matches "ceph --version"
# for a loose definition of "matches"
    echo
    echo "WWWW: ceph_rpm_version_test"
    set -x
    rpm -q ceph-common
    set +x
    local RPM_NAME=$(rpm -q ceph-common)
    local RPM_CEPH_VERSION=$(perl -e '"'"$RPM_NAME"'" =~ m/ceph-common-(\d+\.\d+\.\d+)/; print "$1\n";')
    echo "According to RPM, the ceph upstream version is ->$RPM_CEPH_VERSION<-"
    test -n "$RPM_CEPH_VERSION"
    set -x
    ceph --version
    set +x
    local BUFFER=$(ceph --version)
    local CEPH_CEPH_VERSION=$(perl -e '"'"$BUFFER"'" =~ m/ceph version (\d+\.\d+\.\d+)/; print "$1\n";')
    echo "According to \"ceph --version\", the ceph upstream version is ->$CEPH_CEPH_VERSION<-"
    test -n "$RPM_CEPH_VERSION"
    set -x
    test "$RPM_CEPH_VERSION" = "$CEPH_CEPH_VERSION"
    set +x
    echo "ceph_rpm_version_test: OK"
    echo
}

function ceph_daemon_versions_test {
    local strict_versions="$1"
    local version_host=""
    local version_daemon=""
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
    local minutes_to_wait="5"
    local cluster_status=""
    for minute in $(seq 1 "$minutes_to_wait") ; do
        for i in $(seq 1 4) ; do
            set -x
            ceph status
            cluster_status="$(ceph health detail --format json | jq -r .status)"
            set +x
            if [ "$cluster_status" = "HEALTH_OK" ] ; then
                break 2
            else
                _grace_period 15
            fi
        done
        echo "Minutes left to wait: $((minutes_to_wait - minute))"
    done
    if [ "$cluster_status" != "HEALTH_OK" ] ; then
        echo "Failed to reach HEALTH_OK even after waiting for $minutes_to_wait minutes"
        exit 1
    fi
    echo "ceph_health_test: OK"
    echo
}

function maybe_wait_for_osd_nodes_test {
    local expected_osd_nodes="$1"
    local actual_osd_nodes=""
    local minutes_to_wait="5"
    echo
    echo "WWWW: maybe_wait_for_osd_nodes_test"
    if [ "$expected_osd_nodes" ] ; then
        echo "Waiting up to $minutes_to_wait minutes for OSD nodes to show up..."
        for minute in $(seq 1 "$minutes_to_wait") ; do
            for i in $(seq 1 4) ; do
                set -x
                actual_osd_nodes="$(json_osd_nodes)"
                set +x
                if [ "$actual_osd_nodes" = "$expected_osd_nodes" ] ; then
                    break 2
                else
                    _grace_period 15
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
    else
        echo "No OSD nodes expected: nothing to wait for."
    fi
    echo "maybe_wait_for_osd_nodes_test: OK"
    echo
}

function mgr_is_available_test {
    echo
    echo "WWWW: mgr_is_available_test"
    test "$(json_mgr_is_available)"
    echo "mgr_is_available_test: OK"
    echo
}

function number_of_nodes_actual_vs_expected_test {
    echo
    echo "WWWW: number_of_nodes_actual_vs_expected_test"
    set -x
    local actual_total_nodes="$(json_total_nodes)"
    local actual_mgr_nodes="$(json_total_mgrs)"
    local actual_mon_nodes="$(json_total_mons)"
    local actual_osd_nodes="$(json_osd_nodes)"
    local actual_osds="$(json_total_osds)"
    set +x
    local all_green="yes"
    local expected_total_nodes=""
    local expected_mgr_nodes=""
    local expected_mon_nodes=""
    local expected_osd_nodes=""
    local expected_osds=""
    [ -z "$TOTAL_NODES" ] && expected_total_nodes="$actual_total_nodes" || expected_total_nodes="$TOTAL_NODES"
    [ -z "$MGR_NODES" ] && expected_mgr_nodes="$actual_mgr_nodes" || expected_mgr_nodes="$MGR_NODES"
    [ -z "$MON_NODES" ] && expected_mon_nodes="$actual_mon_nodes" || expected_mon_nodes="$MON_NODES"
    [ -z "$OSD_NODES" ] && expected_osd_nodes="$actual_osd_nodes" || expected_osd_nodes="$OSD_NODES"
    [ -z "$OSDS" ] && expected_osds="$actual_osds" || expected_osds="$OSDS"
    echo "total nodes actual/expected:  $actual_total_nodes/$expected_total_nodes"
    [ "$actual_mon_nodes" = "$expected_mon_nodes" ] || all_green=""
    echo "MON nodes actual/expected:    $actual_mon_nodes/$expected_mon_nodes"
    [ "$actual_mon_nodes" = "$expected_mon_nodes" ] || all_green=""
    echo "MGR nodes actual/expected:    $actual_mgr_nodes/$expected_mgr_nodes"
    [ "$actual_mgr_nodes" = "$expected_mgr_nodes" ] || all_green=""
    echo "OSD nodes actual/expected:    $actual_osd_nodes/$expected_osd_nodes"
    [ "$actual_osd_nodes" = "$expected_osd_nodes" ] || all_green=""
    echo "total OSDs actual/expected:   $actual_osds/$expected_osds"
    [ "$actual_osds" = "$expected_osds" ] || all_green=""
#    echo "MDS nodes expected:     $MDS_NODES"
#    echo "RGW nodes expected:     $RGW_NODES"
#    echo "IGW nodes expected:     $IGW_NODES"
#    echo "NFS-Ganesha expected:   $NFS_GANESHA_NODES"
    if [ ! "$all_green" ] ; then
        echo "Actual number of nodes/node types/OSDs differs from expected number"
        exit 1
    fi
    echo "number_of_nodes_actual_vs_expected_test: OK"
    echo
}
