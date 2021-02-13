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
# shellcheck disable=SC1090
# shellcheck disable=SC1091
source "$BASEDIR/common/rgw.sh"


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

function assert_reboot_not_needed {
    echo
    echo "WWWW: assert_reboot_not_needed"
    local success
    success="yes"
    local nodes_arr
    local node_count
    node_count="0"
    local node_under_test
    local n
    local IFS
    IFS=","
    read -r -a nodes_arr <<<"$NODE_LIST"
    for (( n=0; n<${#nodes_arr[*]}; n++ )) ; do
        node_under_test="${nodes_arr[n]}"
        node_under_test="${node_under_test//[$'\t\r\n']}"
        node_count="$((node_count + 1))"
        if ssh "$node_under_test" zypper ps -s | grep 'No processes using deleted files found' ; then
            success="yes"
        else
            set +e -x
            zypper ps -s
            hostname --fqdn
            set +x -e
            success=""
            break
        fi
    done
    echo
    echo "WWWW: assert_reboot_not_needed: Checked $node_count of ${#nodes_arr[*]} nodes"
    echo
    if [ "$node_count" = "${#nodes_arr[*]}" ] ; then
        true
    else
        success=""
    fi        
    if [ "$success" ] ; then
        echo "WWWW: assert_reboot_not_needed: OK"
        echo
    else
        echo "WARNING: Running processes using deleted files detected!"
        echo
        echo "Since the presence of running processes using deleted files can"
        echo "skew the test results, it would be better to reboot the cluster"
        echo "before running qa-test."
        echo
        echo "WWWW: assert_reboot_not_needed: WARN"
        echo
    fi
}

function support_cop_out_test {
    set +x
    local supported
    supported="sesdev-qa supports this OS"
    local not_supported
    not_supported="sesdev-qa does not currently support this OS"
    echo
    echo "WWWW: support_cop_out_test"
    echo "Detected operating system $NAME $VERSION_ID"
    case "$ID" in
        opensuse-tumbleweed)
            echo "$supported" ;;
        opensuse*|suse|sles)
            case "$VERSION_ID" in
                12.3) echo "$supported" ;;
                15.1) echo "$supported" ;;
                15.2) echo "$supported" ;;
                *) 
                    echo "WARNING: $not_supported"
                    echo "But we'll let it slide this time ;-)"
                    ;;
            esac
            ;;
        *)
            echo "ERROR: $not_supported"
            false
            ;;
    esac
    set +x
    echo "WWWW: support_cop_out_test: OK"
    echo
}

function no_non_oss_repos_test {
    local success
    echo
    echo "WWWW: no_non_oss_repos_test"
    echo "Detected operating system $NAME $VERSION_ID"
    echo
    case "$ID" in
        opensuse*|suse|sles)
            if zypper lr -u | grep 'non-oss' ; then
                echo
                echo "ERROR: Non-OSS repo(s) detected!"
            else
                success="not_empty"
            fi
            ;;
        *)
            echo "ERROR: Unsupported OS ->$ID<-"
            ;;
    esac
    if [ "$success" ] ; then
        echo "WWWW: no_non_oss_repos_test: OK"
        echo
    else
        echo "WWWW: no_non_oss_repos_test: FAIL"
        echo
        false
    fi
}

function make_salt_master_an_admin_node_test {
    local arbitrary_mon_node
    echo
    echo "WWWW: make_salt_master_an_admin_node_test"
    _zypper_install_on_master ceph-common
    set -x
    mkdir -p "/etc/ceph"
    if [ -f "$ADMIN_KEYRING" ] || [ -f "$CEPH_CONF" ] ; then
        true
    else
        arbitrary_mon_node="$(_first_x_node mon)"
        if [ ! -f "$ADMIN_KEYRING" ] ; then
            _copy_file_from_minion_to_master "$arbitrary_mon_node" "$ADMIN_KEYRING"
            chmod 0600 "$ADMIN_KEYRING"
        fi
        if [ ! -f "$CEPH_CONF" ] ; then
            _copy_file_from_minion_to_master "$arbitrary_mon_node" "$CEPH_CONF"
        fi
    fi
    test -f "$ADMIN_KEYRING"
    test -f "$CEPH_CONF"
    set +x
    echo "WWWW: make_salt_master_an_admin_node_test: OK"
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
    echo "WWWW: ceph_rpm_version_test: OK"
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
    echo "WWWW: ceph_daemon_versions_test: OK"
    echo
}

function ceph_cluster_running_test {
    echo
    echo "WWWW: ceph_cluster_running_test"
    _ceph_cluster_running
    echo "WWWW: ceph_cluster_running_test: OK"
    echo
}

function maybe_wait_for_osd_nodes_test {
    local expected_osd_nodes="$1"
    echo
    echo "WWWW: maybe_wait_for_osd_nodes_test"
    if [ "$expected_osd_nodes" -gt "0" ] ; then
        local actual_osd_nodes
        local minutes_to_wait
        minutes_to_wait="5"
        local minute
        local i
        local success
        echo "Waiting up to $minutes_to_wait minutes for all $expected_osd_nodes OSD node(s) to show up..."
        for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
            for (( i=1; i<=4; i++ )) ; do
                set -x
                actual_osd_nodes="$(json_osd_nodes)"
                set +x
                if [ "$actual_osd_nodes" = "$expected_osd_nodes" ] ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i of 4 in minute $minute"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
        if [ "$success" ] ; then
            echo "WWWW: maybe_wait_for_osd_nodes_test: OK"
            echo
        else
            echo "$expected_osd_nodes OSD nodes did not appear even after waiting $minutes_to_wait minutes. Giving up."
            echo "WWWW: maybe_wait_for_osd_nodes_test: FAIL"
            echo
            false
        fi
    else
        echo "No OSD nodes expected: nothing to wait for."
        echo "maybe_wait_for_osd_nodes_test: SKIPPED"
        echo
    fi
}

function maybe_wait_for_mdss_test {
    local expected_mdss="$1"
    echo
    echo "WWWW: maybe_wait_for_mdss_test"
    if [ "$expected_mdss" -gt "0" ] ; then
        local actual_mdss
        local minutes_to_wait
        minutes_to_wait="5"
        local metadata_mdss
        local minute
        local i
        local success
        echo "Waiting up to $minutes_to_wait minutes for all $expected_mdss MDS daemon(s) to show up..."
        for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
            for (( i=1; i<=4; i++ )) ; do
                set -x
                metadata_mdss="$(json_metadata_mdss)"
                actual_mdss="$(json_total_mdss)"
                set +x
                if [ "$actual_mdss" = "$expected_mdss" ] && [ "$actual_mdss" = "$metadata_mdss" ] ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i of 4 in minute $minute"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
        if [ "$success" ] ; then
            echo "WWWW: maybe_wait_for_mdss_test: OK"
            echo
        else
            echo "$expected_mdss MDS daemons did not appear even after waiting $minutes_to_wait minutes. Giving up."
            echo "WWWW: maybe_wait_for_mdss_test: FAIL"
            echo
            false
        fi
    else
        echo "No MDSs expected: nothing to wait for."
        echo "maybe_wait_for_mdss_test: SKIPPED"
        echo
    fi
}

function maybe_wait_for_rgws_test {
    local expected_rgws="$1"
    echo
    echo "WWWW: maybe_wait_for_rgws_test"
    if [ "$expected_rgws" -gt "0" ] ; then
        local actual_rgws
        local minutes_to_wait
        minutes_to_wait="5"
        local minute
        local i
        local success
        echo "Waiting up to $minutes_to_wait minutes for all $expected_rgws RGW daemon(s) to show up..."
        for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
            for (( i=1; i<=4; i++ )) ; do
                set -x
                actual_rgws="$(json_total_rgws)"
                set +x
                if [ "$actual_rgws" = "$expected_rgws" ] ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i of 4 in minute $minute"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
        if [ "$success" ] ; then
            echo "WWWW: maybe_wait_for_rgws_test: OK"
            echo
        else
            echo "$expected_rgws RGW daemons did not appear even after waiting $minutes_to_wait minutes. Giving up."
            echo "WWWW: maybe_wait_for_rgws_test: FAIL"
            echo
            false
        fi
    else
        echo "No RGWs expected: nothing to wait for."
        echo "maybe_wait_for_rgws_test: SKIPPED"
        echo
    fi
}

function _wait_for {
    # this function uses json_ses7_orch_{ls,ps}, which only work in
    # {octopus,ses7,pacific}
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local what="$1"
        local expected="$2"
        local orch_ps
        local orch_ls
        local minutes_to_wait
        minutes_to_wait="5"
        local minute
        local i
        local success
        echo "Waiting up to $minutes_to_wait minutes for all $expected $what daemon(s) to show up..."
        for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
            for (( i=1; i<=4; i++ )) ; do
                set -x
                orch_ls="$(json_ses7_orch_ls "$what")"
                orch_ps="$(json_ses7_orch_ps "$what")"
                set +x
                if [ "$orch_ls" = "$expected" ] && [ "$orch_ps" = "$expected" ] ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i of 4 in minute $minute"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
        if [ "$success" ] ; then
            true
        else
            echo "$expected_nfss $what daemons did not appear even after waiting $minutes_to_wait minutes. Giving up."
            echo
            false
        fi
    fi
}

function maybe_wait_for_nfss_test {
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local expected_nfss="$1"
        echo
        echo "WWWW: maybe_wait_for_nfss_test"
        if [ "$expected_nfss" -gt "0" ] ; then
            _wait_for nfs "$expected_nfss"
            echo "WWWW: maybe_wait_for_nfss_test: OK"
            echo
        else
            echo "No NFSs expected: nothing to wait for."
            echo "WWWW: maybe_wait_for_nfss_test: SKIPPED"
            echo
        fi
    fi
}

function maybe_wait_for_igws_test {
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local expected_igws="$1"
        echo
        echo "WWWW: maybe_wait_for_igws_test"
        if [ "$expected_igws" -gt "0" ] ; then
            _wait_for iscsi "$expected_igws"
            echo "WWWW: maybe_wait_for_igws_test: OK"
            echo
        else
            echo "No IGWs expected: nothing to wait for."
            echo "WWWW: maybe_wait_for_igws_test: SKIPPED"
            echo
        fi
    fi
}

function maybe_wait_for_grafanas_test {
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local expected_grafanas="$1"
        echo
        echo "WWWW: maybe_wait_for_grafanas_test"
        if [ "$expected_grafanas" -gt "0" ] ; then
            _wait_for grafana "$expected_grafanas"
            echo "WWWW: maybe_wait_for_grafanas_test: OK"
            echo
        else
            echo "No Grafanas expected: nothing to wait for."
            echo "WWWW: maybe_wait_for_grafanas_test: SKIPPED"
            echo
        fi
    fi
}

function mgr_is_available_test {
    echo
    echo "WWWW: mgr_is_available_test"
    test "$(json_mgr_is_available)"
    echo "WWWW: mgr_is_available_test: OK"
    echo
}

function number_of_daemons_expected_vs_metadata_test {
    # only works for core daemons
    echo
    echo "WWWW: number_of_daemons_expected_vs_metadata_test"
    local metadata_mgrs
    metadata_mgrs="$(json_metadata_mgrs)"
    local metadata_mons
    metadata_mons="$(json_metadata_mons)"
    local metadata_mdss
    metadata_mdss="$(json_metadata_mdss)"
    local metadata_osds
    metadata_osds="$(json_metadata_osds)"
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
        echo "MON daemons (metadata/expected): $metadata_mons/$expected_mons"
        [ "$metadata_mons" = "$expected_mons" ] || success=""
    fi
    if [ "$expected_mgrs" ] ; then
        echo "MGR daemons (metadata/expected): $metadata_mgrs/$expected_mgrs"
        if [ "$metadata_mgrs" = "$expected_mgrs" ] ; then
            true  # normal success case
        elif [ "$expected_mgrs" -gt "1" ] && [ "$metadata_mgrs" = "$((expected_mgrs + 1))" ] ; then
            true  # workaround for https://tracker.ceph.com/issues/45093
        else
            success=""
        fi
    fi
    if [ "$expected_mdss" ] ; then
        echo "MDS daemons (metadata/expected): $metadata_mdss/$expected_mdss"
        [ "$metadata_mdss" = "$expected_mdss" ] || success=""
    fi
    if [ "$expected_osds" ] ; then
        echo "OSD daemons (metadata/expected): $metadata_osds/$expected_osds"
        [ "$metadata_osds" = "$expected_osds" ] || success=""
    fi
    if [ "$success" ] ; then
        echo "WWWW: number_of_daemons_expected_vs_metadata_test: OK"
        echo
    else
        echo "ERROR: Detected disparity between expected number of daemons and cluster metadata!"
        echo "WWWW: number_of_daemons_expected_vs_metadata_test: FAIL"
        echo
        false
    fi
}

function number_of_services_expected_vs_orch_ls_test {
    echo
    echo "WWWW: number_of_services_expected_vs_orch_ls_test"
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local orch_ls_mgrs
        orch_ls_mgrs="$(json_ses7_orch_ls mgr)"
        local orch_ls_mons
        orch_ls_mons="$(json_ses7_orch_ls mon)"
        local orch_ls_mdss
        orch_ls_mdss="$(json_ses7_orch_ls mds)"
        ## commented-out osds pending resolution of
        ## - https://bugzilla.suse.com/show_bug.cgi?id=1172791
        ## - https://github.com/SUSE/sesdev/pull/203
        # local orch_ls_osds
        # orch_ls_osds="$(json_ses7_orch_ls osd)"
        local orch_ls_rgws
        orch_ls_rgws="$(json_ses7_orch_ls rgw)"
        local orch_ls_nfss
        orch_ls_nfss="$(json_ses7_orch_ls nfs)"
        local orch_ls_igws
        orch_ls_igws="$(json_ses7_orch_ls iscsi)"
        local orch_ls_prometheuses
        orch_ls_prometheuses="$(json_ses7_orch_ls prometheus)"
        local orch_ls_grafanas
        orch_ls_grafanas="$(json_ses7_orch_ls grafana)"
        local orch_ls_alertmanagers
        orch_ls_alertmanagers="$(json_ses7_orch_ls alertmanager)"
        local orch_ls_node_exporters
        orch_ls_node_exporters="$(json_ses7_orch_ls node-exporter)"
        local success
        success="yes"
        local expected_mgrs
        local expected_mons
        local expected_mdss
        local expected_osds
        local expected_rgws
        local expected_nfss
        local expected_igws
        local expected_prometheuses
        local expected_grafanas
        local expected_alertmanagers
        local expected_node_exporters
        [ "$MGR_NODES" ] && expected_mgrs="$MGR_NODES"
        [ "$MON_NODES" ] && expected_mons="$MON_NODES"
        [ "$MDS_NODES" ] && expected_mdss="$MDS_NODES"
        [ "$OSDS" ]      && expected_osds="$OSDS"
        [ "$RGW_NODES" ] && expected_rgws="$RGW_NODES"
        [ "$NFS_NODES" ] && expected_nfss="$NFS_NODES"
        [ "$IGW_NODES" ] && expected_igws="$IGW_NODES"
        [ "$PROMETHEUS_NODES" ] && expected_prometheuses="$PROMETHEUS_NODES"
        [ "$GRAFANA_NODES" ] && expected_grafanas="$GRAFANA_NODES"
        [ "$ALERTMANAGER_NODES" ] && expected_alertmanagers="$ALERTMANAGER_NODES"
        [ "$NODE_EXPORTER_NODES" ] && expected_node_exporters="$NODE_EXPORTER_NODES"
        echo "MGR services (orch ls/expected): $orch_ls_mgrs/$expected_mgrs"
        if [ "$orch_ls_mgrs" = "$expected_mgrs" ] ; then
            true  # normal success case
        elif [ "$expected_mgrs" -gt "1" ] && [ "$orch_ls_mgrs" = "$((expected_mgrs + 1))" ] ; then
            true  # workaround for https://tracker.ceph.com/issues/45093
        else
            success=""
        fi
        echo "MON services (orch ls/expected): $orch_ls_mons/$expected_mons"
        [ "$orch_ls_mons" = "$expected_mons" ] || success=""
        echo "MDS services (orch ls/expected): $orch_ls_mdss/$expected_mdss"
        [ "$orch_ls_mdss" = "$expected_mdss" ] || success=""
        # echo "OSDs orch ls/expected: $orch_ls_osds/$expected_osds"
        # [ "$orch_ls_osds" = "$expected_osds" ] || success=""
        echo "RGW services (orch ls/expected): $orch_ls_rgws/$expected_rgws"
        [ "$orch_ls_rgws" = "$expected_rgws" ] || success=""
        echo "NFS services (orch ls/expected): $orch_ls_nfss/$expected_nfss"
        [ "$orch_ls_nfss" = "$expected_nfss" ] || success=""
        echo "IGW services (orch ls/expected): $orch_ls_igws/$expected_igws"
        [ "$orch_ls_igws" = "$expected_igws" ] || success=""
        echo "Prometheus services (orch ls/expected): $orch_ls_prometheuses/$expected_prometheuses"
        [ "$orch_ls_prometheuses" = "$expected_prometheuses" ] || success=""
        echo "Grafana services (orch ls/expected): $orch_ls_grafanas/$expected_grafanas"
        [ "$orch_ls_grafanas" = "$expected_grafanas" ] || success=""
        echo "alertmanager services (orch ls/expected): $orch_ls_alertmanagers/$expected_alertmanagers"
        [ "$orch_ls_alertmanagers" = "$expected_alertmanagers" ] || success=""
        echo "node-manager services (orch ls/expected): $orch_ls_node_exporters/$expected_node_exporters"
        [ "$orch_ls_node_exporters" = "$expected_node_exporters" ] || success=""
        if [ "$success" ] ; then
            echo "WWWW: number_of_services_expected_vs_orch_ls_test: OK"
            echo
        else
            echo "ERROR: Detected disparity between expected number of services and \"ceph orch ls\"!"
            echo "WWWW: number_of_services_expected_vs_orch_ls_test: FAIL"
            echo
            false
        fi
    else
        echo "WWWW: number_of_services_expected_vs_orch_ls_test: SKIPPED"
        echo
    fi
}

function _orch_ps_test {
    local success
    success="yes"
    local orch_ps_mgrs
    orch_ps_mgrs="$(json_ses7_orch_ps mgr)"
    local orch_ps_mons
    orch_ps_mons="$(json_ses7_orch_ps mon)"
    local orch_ps_mdss
    orch_ps_mdss="$(json_ses7_orch_ps mds)"
    local orch_ps_rgws
    orch_ps_rgws="$(json_ses7_orch_ps rgw)"
    local orch_ps_nfss
    orch_ps_nfss="$(json_ses7_orch_ps nfs)"
    local orch_ps_igws
    orch_ps_igws="$(json_ses7_orch_ps iscsi)"
    local orch_ps_prometheuses
    orch_ps_prometheuses="$(json_ses7_orch_ps prometheus)"
    local orch_ps_grafanas
    orch_ps_grafanas="$(json_ses7_orch_ps grafana)"
    local orch_ps_alertmanagers
    orch_ps_alertmanagers="$(json_ses7_orch_ps alertmanager)"
    local orch_ps_node_exporters
    orch_ps_node_exporters="$(json_ses7_orch_ps node-exporter)"
    ## commented-out osds pending resolution of
    ## - https://bugzilla.suse.com/show_bug.cgi?id=1172791
    ## - https://github.com/SUSE/sesdev/pull/203
    # local orch_ps_osds
    # orch_ps_osds="$(json_ses7_orch_ps osd)"
    local expected_mgrs
    local expected_mons
    local expected_mdss
    local expected_osds
    local expected_rgws
    local expected_nfss
    local expected_igws
    local expected_prometheuses
    local expected_grafanas
    local expected_alertmanagers
    local expected_node_exporters
    [ "$MGR_NODES" ] && expected_mgrs="$MGR_NODES"
    [ "$MON_NODES" ] && expected_mons="$MON_NODES"
    [ "$MDS_NODES" ] && expected_mdss="$MDS_NODES"
    [ "$OSDS" ]      && expected_osds="$OSDS"
    [ "$RGW_NODES" ] && expected_rgws="$RGW_NODES"
    [ "$NFS_NODES" ] && expected_nfss="$NFS_NODES"
    [ "$IGW_NODES" ] && expected_igws="$IGW_NODES"
    [ "$PROMETHEUS_NODES" ] && expected_prometheuses="$PROMETHEUS_NODES"
    [ "$GRAFANA_NODES" ] && expected_grafanas="$GRAFANA_NODES"
    [ "$ALERTMANAGER_NODES" ] && expected_alertmanagers="$ALERTMANAGER_NODES"
    [ "$NODE_EXPORTER_NODES" ] && expected_node_exporters="$NODE_EXPORTER_NODES"
    echo "MGR daemons (orch ps/expected): $orch_ps_mgrs/$expected_mgrs"
    if [ "$orch_ps_mgrs" = "$expected_mgrs" ] ; then
        true  # normal success case
    elif [ "$expected_mgrs" -gt "1" ] && [ "$orch_ps_mgrs" = "$((expected_mgrs + 1))" ] ; then
        true  # workaround for https://tracker.ceph.com/issues/45093
    else
        success=""
    fi
    echo "MON daemons (orch ps/expected): $orch_ps_mons/$expected_mons"
    [ "$orch_ps_mons" = "$expected_mons" ] || success=""
    echo "MDS daemons (orch ps/expected): $orch_ps_mdss/$expected_mdss"
    [ "$orch_ps_mdss" = "$expected_mdss" ] || success=""
    # echo "OSDs orch ps/expected: $orch_ps_osds/$expected_osds"
    # [ "$orch_ps_osds" = "$expected_osds" ] || success=""
    echo "RGW daemons (orch ps/expected): $orch_ps_rgws/$expected_rgws"
    [ "$orch_ps_rgws" = "$expected_rgws" ] || success=""
    echo "NFS daemons (orch ps/expected): $orch_ps_nfss/$expected_nfss"
    [ "$orch_ps_nfss" = "$expected_nfss" ] || success=""
    echo "IGW daemons (orch ps/expected): $orch_ps_igws/$expected_igws"
    [ "$orch_ps_igws" = "$expected_igws" ] || success=""
    echo "Prometheus daemons (orch ps/expected): $orch_ps_prometheuses/$expected_prometheuses"
    [ "$orch_ps_prometheuses" = "$expected_prometheuses" ] || success=""
    echo "Grafana daemons (orch ps/expected): $orch_ps_grafanas/$expected_grafanas"
    [ "$orch_ps_grafanas" = "$expected_grafanas" ] || success=""
    echo "alertmanager daemons (orch ps/expected): $orch_ps_alertmanagers/$expected_alertmanagers"
    [ "$orch_ps_alertmanagers" = "$expected_alertmanagers" ] || success=""
    echo "node-manager services (orch ps/expected): $orch_ps_node_exporters/$expected_node_exporters"
    [ "$orch_ps_node_exporters" = "$expected_node_exporters" ] || success=""
    if [ "$success" ] ; then
        return 0
    else
        echo "ERROR: Detected disparity between expected number of services and \"ceph orch ps\"!"
        return 1
    fi
}

function number_of_services_expected_vs_orch_ps_test {
    echo
    echo "WWWW: number_of_services_expected_vs_orch_ps_test"
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        local minutes_to_wait
        minutes_to_wait="5"
        local minute
        local i
        local success
        echo "Waiting up to $minutes_to_wait minutes for \"ceph orch ps\" to list all expected daemons"
        for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
            for (( i=1; i<=4; i++ )) ; do
                if _orch_ps_test ; then
                    success="not_empty"
                    break 2
                else
                    _grace_period 15 "$i of 4 in minute $minute"
                fi
            done
            echo "Minutes left to wait: $((minutes_to_wait - minute))"
        done
        if [ "$success" ] ; then
            echo "WWWW: number_of_services_expected_vs_orch_ps_test: OK"
            echo
        else
            echo "WWWW: number_of_services_expected_vs_orch_ps_test: FAIL"
            echo
            false
        fi
    else
        echo "WWWW: number_of_services_expected_vs_orch_ps_test: SKIPPED"
        echo
    fi
}

function number_of_daemons_expected_vs_actual {
    echo
    echo "WWWW: number_of_nodes_actual_vs_expected_test"
    local actual_total_nodes
    actual_total_nodes="$(json_total_nodes)"
    local actual_mgr_nodes
    actual_mgr_nodes="$(json_total_mgrs)"
    local actual_mon_nodes
    actual_mon_nodes="$(json_total_mons)"
    local actual_mds_nodes
    actual_mds_nodes="$(json_total_mdss)"
    local actual_rgw_nodes
    actual_rgw_nodes="$(json_total_rgws)"
    local actual_osd_nodes
    actual_osd_nodes="$(json_osd_nodes)"
    local actual_osds
    actual_osds="$(json_total_osds)"
    local success
    success="yes"
    local expected_total_nodes
    local expected_mgr_nodes
    local expected_mon_nodes
    local expected_mds_nodes
    local expected_rgw_nodes
    local expected_osd_nodes
    local expected_osds
    [ "$TOTAL_NODES" ] && expected_total_nodes="$TOTAL_NODES"
    [ "$MGR_NODES" ]   && expected_mgr_nodes="$MGR_NODES"
    [ "$MON_NODES" ]   && expected_mon_nodes="$MON_NODES"
    [ "$MDS_NODES" ]   && expected_mds_nodes="$MDS_NODES"
    [ "$RGW_NODES" ]   && expected_rgw_nodes="$RGW_NODES"
    [ "$OSD_NODES" ]   && expected_osd_nodes="$OSD_NODES"
    [ "$OSDS" ]        && expected_osds="$OSDS"
    if [ "$expected_total_nodes" ] ; then
        echo "total nodes (actual/expected):  $actual_total_nodes/$expected_total_nodes"
        [ "$actual_total_nodes" = "$expected_total_nodes" ] || success=""
    fi
    if [ "$expected_mon_nodes" ] ; then
        echo "MON nodes (actual/expected):    $actual_mon_nodes/$expected_mon_nodes"
        [ "$actual_mon_nodes" = "$expected_mon_nodes" ] || success=""
    fi
    if [ "$expected_mgr_nodes" ] ; then
        echo "MGR nodes (actual/expected):    $actual_mgr_nodes/$expected_mgr_nodes"
        if [ "$actual_mgr_nodes" = "$expected_mgr_nodes" ] ; then
            true  # normal success case
        elif [ "$expected_mgr_nodes" -gt "1" ] && [ "$actual_mgr_nodes" = "$((expected_mgr_nodes + 1))" ] ; then
            true  # workaround for https://tracker.ceph.com/issues/45093
        else
            success=""
        fi
    fi
    if [ "$expected_mds_nodes" ] ; then
        echo "MDS nodes (actual/expected):    $actual_mds_nodes/$expected_mds_nodes"
        [ "$actual_mds_nodes" = "$expected_mds_nodes" ] || success=""
    fi
    if [ "$expected_rgw_nodes" ] ; then
        echo "RGW nodes (actual/expected):    $actual_rgw_nodes/$expected_rgw_nodes"
        [ "$actual_rgw_nodes" = "$expected_rgw_nodes" ] || success=""
    fi
    if [ "$expected_osd_nodes" ] ; then
        echo "OSD nodes (actual/expected):    $actual_osd_nodes/$expected_osd_nodes"
        [ "$actual_osd_nodes" = "$expected_osd_nodes" ] || success=""
    fi
    if [ "$expected_osds" ] ; then
        echo "total OSDs (actual/expected):   $actual_osds/$expected_osds"
        [ "$actual_osds" = "$expected_osds" ] || success=""
    fi
    if [ "$success" ] ; then
        echo "WWWW: number_of_nodes_actual_vs_expected_test: OK"
        echo
    else
        echo "ERROR: Detected disparity between expected and actual numbers of nodes/daemons"
        echo "WWWW: number_of_nodes_actual_vs_expected_test: FAIL"
        echo
        false
    fi
}

function ceph_health_test {
# wait for up to 30 minutes for cluster to reach HEALTH_OK
    echo
    echo "WWWW: ceph_health_test"
    local minutes_to_wait
    minutes_to_wait="30"
    local cluster_status
    local minute
    local i
    for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
        for (( i=1; i<=4; i++ )) ; do
            set -x
            ceph status
            cluster_status="$(ceph health detail --format json | jq -r .status)"
            set +x
            if [ "$cluster_status" = "HEALTH_OK" ] ; then
                break 2
            else
                _grace_period 15 "$i of 4 in minute $minute"
            fi
        done
        echo "Minutes left to wait: $((minutes_to_wait - minute))"
    done
    if [ "$cluster_status" = "HEALTH_OK" ] ; then
        echo "WWWW: ceph_health_test: OK"
        echo
    else
        echo "HEALTH_OK not reached even after waiting for $minutes_to_wait minutes"
        echo "WWWW: ceph_health_test: FAIL"
        echo
        false
    fi
}

function maybe_rgw_smoke_test {
# assert that the Object Gateway is alive on the node where it is expected to be
    echo
    echo "WWWW: maybe_rgw_smoke_test"
    if [ "$RGW_NODE_LIST" ] ; then
        install_rgw_test_dependencies
        local rgw_nodes_arr
        local rgw_node_count
        rgw_node_count="0"
        local rgw_node_under_test
        local IFS
        IFS=","
        read -r -a rgw_nodes_arr <<<"$RGW_NODE_LIST"
        for (( n=0; n<${#rgw_nodes_arr[*]}; n++ )) ; do
            rgw_node_under_test="${rgw_nodes_arr[n]}"
            rgw_node_under_test="${rgw_node_under_test//[$'\t\r\n']}"
            set -x
            rgw_curl_test "$rgw_node_under_test"
            set +x
            rgw_node_count="$((rgw_node_count + 1))"
        done
        echo "RGW nodes expected/tested: $rgw_node_count/${#rgw_nodes_arr[*]}"
        if [ "$rgw_node_count" = "${#rgw_nodes_arr[*]}" ] ; then
            echo "WWWW: maybe_rgw_smoke_test: OK"
            echo
        else
            echo "WWWW: maybe_rgw_smoke_test: FAIL"
            echo
            false
        fi
    else
        echo "WWWW: maybe_rgw_smoke_test: SKIPPED"
        echo
    fi
}

function cluster_json_test {
    echo "WWWW: cluster_json_test"
    local nodes_arr
    local node_count
    node_count="0"
    local node_under_test
    local n
    local IFS
    IFS=","
    read -r -a nodes_arr <<<"$NODE_LIST"
    for (( n=0; n<${#nodes_arr[*]}; n++ )) ; do
        node_under_test="${nodes_arr[n]}"
        node_under_test="${node_under_test//[$'\t\r\n']}"
        set -x
        ssh "$node_under_test" test -s /home/vagrant/cluster.json
        set +x
        node_count="$((node_count + 1))"
    done
    echo "Total nodes expected/tested: $node_count/${#nodes_arr[*]}"
    if [ "$node_count" = "${#nodes_arr[*]}" ] ; then
        echo "WWWW: cluster_json_test: OK"
        echo
    else
        echo "WWWW: cluster_json_test: FAIL"
        echo
        false
    fi
}

function systemctl_list_units_test {
    echo "WWWW: systemctl_list_units_test"
    # no "readarray -d" in SLE-12-SP3
    local nodes_arr
    local node_count
    node_count="0"
    local node_under_test
    local n
    local fsid
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        fsid="$(_fsid)"
    fi
    local IFS
    IFS=","
    read -r -a nodes_arr <<<"$NODE_LIST"
    for (( n=0; n<${#nodes_arr[*]}; n++ )) ; do
        node_under_test="${nodes_arr[n]}"
        node_under_test="${node_under_test//[$'\t\r\n']}"
        set -x
        # shellcheck disable=SC2029
        ssh "$node_under_test" /home/vagrant/systemctl_test.sh "$fsid"
        set +x
        node_count="$((node_count + 1))"
    done
    echo "Total nodes expected/tested: $node_count/${#nodes_arr[*]}"
    if [ "$node_count" = "${#nodes_arr[*]}" ] ; then
        echo "WWWW: systemctl_list_units_test: OK"
        echo
    else
        echo "WWWW: systemctl_list_units_test: FAIL"
        echo
        false
    fi
}

function osd_objectstore_test {
    echo "WWWW: osd_objectstore_test"
    local expected_objectstore
    [ "$FILESTORE_OSDS" ] && expected_objectstore="filestore" || expected_objectstore="bluestore"
    local osd_objectstore
    osd_objectstore=$(_osd_objectstore)
    local line
    local success
    success="yes"
    local count
    count="0"
    for line in $osd_objectstore ; do
        echo "$line"
        if [ "$line" = "$expected_objectstore" ] ; then
            count="$((count + 1))"
        else
            echo "ERROR: encountered OSD with unexpected objectstore $line"
            success=""
        fi
    done
    echo "$expected_objectstore OSDs (found/expected): $count/$OSDS"
    if [ "$count" = "$OSDS" ] ; then
        true
    else
        success=""
    fi
    if [ "$success" ] ; then
        echo "WWWW: osd_objectstore_test: OK"
        echo
    else
        echo "WWWW: osd_objectstore_test: FAIL"
        echo
        false
    fi
}

function dashboard_branding_not_completely_absent_test {
    echo "WWWW: dashboard_branding_not_completely_absent_test"
    local the_test_is_on
    if [ "$VERSION_ID" = "15.1" ] || [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        if [[ "$(ceph --version)" =~ "ceph version 16" ]] ; then
            # ceph version 16 (pacific) is not expected to have downstream
            # branding
            true
        else
            the_test_is_on="yes"
        fi
    fi
    if [ "$the_test_is_on" ] ; then
        local success
        local dashboard_url
        _zypper_ref_on_master
        _zypper_install_on_master curl
        set -x
        dashboard_url="$(ceph mgr services | jq -r .dashboard)"
        if curl --silent --insecure "$dashboard_url" | grep -i suse ; then
            success="yes"
        fi
        set +x
        if [ "$success" ] ; then
            echo "WWWW: dashboard_branding_not_completely_absent_test: OK"
            echo
        else
            echo "ERROR: SUSE dashboard branding appears to be completely absent!"
            echo "WWWW: dashboard_branding_not_completely_absent_test: FAIL"
            echo
            false
        fi
    else
        echo "WWWW: dashboard_branding_not_completely_absent_test: SKIPPED"
        echo
    fi
}

function nfs_maybe_list_objects_in_recovery_pool_test {
    local skipped
    skipped="yes"
    local result
    local tmpfile
    tmpfile="$(mktemp)"
    echo "WWWW: nfs_maybe_list_objects_in_recovery_pool_test"
    echo
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        if [ "$NFS_NODE_LIST" ] && [ "$MDS_NODE_LIST" ] ; then
            # NFS Recovery Pool expected to exist
            skipped=""
            set -x
            rados --pool nfs-ganesha --namespace sesdev_nfs ls | tee "$tmpfile"
            set +x
            if [ -s "$tmpfile" ] ; then
                result="OK"
            else
                echo "WWWW: nfs_maybe_list_objects_in_recovery_pool_test: FAIL"
                echo
                false
            fi
        fi
    fi
    if [ "$skipped" ] ; then
        result="SKIPPED"
    fi
    echo "WWWW: nfs_maybe_list_objects_in_recovery_pool_test: $result"
    echo
}

function nfs_maybe_create_export {
    local skipped
    skipped="yes"
    local result
    local tmpfile
    tmpfile="$(mktemp)"
    local length
    echo "WWWW: nfs_maybe_create_export"
    echo
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        if [ "$NFS_NODE_LIST" ] && [ "$MDS_NODE_LIST" ] ; then
            skipped=""
            set -x
            ceph nfs export create cephfs sesdev_fs sesdev_nfs "/sesdev_nfs"
            ceph nfs export ls sesdev_nfs --detailed | tee "$tmpfile"
            length="$(<"$tmpfile" jq -r 'length')"
            set +x
            if [ -s "$tmpfile" ] && [ "$length" = "1" ] ; then
                result="OK"
            else
                echo "WWWW: nfs_maybe_create_export: FAIL"
                echo
                false
            fi
        fi
    fi
    if [ "$skipped" ] ; then
        result="SKIPPED"
    fi
    echo "WWWW: nfs_maybe_create_export: $result"
    echo
}

function nfs_maybe_mount_export_and_touch_file {
    local skipped
    skipped="yes"
    local result
    local tmpfile
    tmpfile="$(mktemp)"
    local first_nfs_node
    first_nfs_node="$(_first_x_node "nfs")"
    local count
    local max_count_we_can_tolerate
    local mount_point
    mount_point="/mnt/nfs"
    echo "WWWW: nfs_maybe_mount_export_and_touch_file"
    echo
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        if [ "$DEPLOYMENT_VERSION" = "pacific" ] ; then
            echo "THIS TEST HAS BEEN DISABLED BECAUSE IT DOES NOT PASS ON PACIFIC"
            echo "SEE https://github.com/SUSE/sesdev/issues/491 FOR MORE INFORMATION"
        elif [ "$NFS_NODE_LIST" ] && [ "$MDS_NODE_LIST" ] ; then
            if [ "$first_nfs_node" ] ; then
                skipped=""
                _zypper_ref_on_master
                _zypper_install_on_master "nfs-client"
                set -x
                rm -rf "$mount_point"
                mkdir -p "$mount_point"
                mount -t nfs4 "$first_nfs_node:/sesdev_nfs" "$mount_point"
                set +x
                echo "Wait for grace period to expire..."
                count="0"
                max_count_we_can_tolerate="30"
                while true ; do
                    count="$(( count + 1 ))"
                    if touch "$mount_point/bubba" ; then
                        break
                    fi
                    if [ "$count" -gt "$max_count_we_can_tolerate" ] ; then
                        echo "Unable to touch a file in the NFS export even after waiting for the grace period to expire"
                        echo "WWWW: nfs_maybe_mount_export_and_touch_file: FAIL"
                        echo
                        false
                    fi
                    sleep 5
                    echo "$count times 5 seconds"
                done
                echo "Grace period expired!"
                set -x
                echo "hubba" > "$mount_point/bubba"
                test -s "$mount_point/bubba"
                test "$(cat "$mount_point/bubba")" = "hubba"
                umount "$mount_point"
                set +x
                result="OK"
            else
                echo "BADNESS: NO NFS NODES IN CLUSTER, YET I AM SUPPOSED TO RUN AN NFS-RELATED TEST???"
                exit 1
            fi
        fi
    fi
    if [ "$skipped" ] ; then
        result="SKIPPED"
    fi
    echo "WWWW: nfs_maybe_mount_export_and_touch_file: $result"
    echo
}

function _monitoring_wait_for {
    local what="$1"
    local node="$2"
    local port="$3"
    set -e
    set +x
    echo "Waiting for $what on $node to start listening on its port"
    minutes_to_wait="20"
    local minute
    local i
    local success
    set +H
    echo -en "" > /tmp/wfp.sh
    echo -en "#!/bin/bash\n" >> /tmp/wfp.sh
    echo -en "ss -ntulw | grep '\*\:$port'\n" >> /tmp/wfp.sh
    scp "/tmp/wfp.sh" "$node:/home/vagrant/is_listening.sh"
    echo "Waiting up to $minutes_to_wait minutes for $what on $node to start listening on its port $port"
    for (( minute=1; minute<=minutes_to_wait; minute++ )) ; do
        for (( i=1; i<=12; i++ )) ; do
            echo "Pinging $what on $node... ($i of 12)"
            if ssh "$node" "bash" "/home/vagrant/is_listening.sh" ; then
                break 2
            fi
            sleep 5
        done
        echo "Trying for another minute!"
    done
}

function _monitoring_smoke_test {
    # assert that monitoring daemon (Prometheus, Grafana, etc.) is alive on the
    # node where it is expected to be
    local daemon_type="$1"
    local grep_for="$2"
    local ssl="$3"
    local temp_file
    temp_file="$(mktemp)"
    local nodes_list
    if [ "$daemon_type" = "prometheus" ] ; then
        nodes_list="$PROMETHEUS_NODE_LIST"
    elif [ "$daemon_type" = "grafana" ] ; then
        nodes_list="$GRAFANA_NODE_LIST"
    elif [ "$daemon_type" = "alertmanager" ] ; then
        nodes_list="$ALERTMANAGER_NODE_LIST"
    elif [ "$daemon_type" = "node-exporter" ] ; then
        nodes_list="$NODE_EXPORTER_NODE_LIST"
    else
        echo "_monitoring_smoke_test: badness, bailing out!"
        false
    fi
    echo
    echo "WWWW: ${daemon_type}_smoke_test"
    local run_the_test="yes"
    [ -z "$nodes_list" ]       && run_the_test=""
    [ "$VERSION_ID" = "12.3" ] && run_the_test=""
    if [ "$daemon_type" = "alertmanager" ] || [ "$daemon_type" = "node-exporter" ] ; then
        [ "$VERSION_ID" = "15.1" ] && run_the_test=""
    fi
    if [ "$run_the_test" ] ; then
        _zypper_ref_on_master
        _zypper_install_on_master curl
        local default_port
        if [ "$daemon_type" = "prometheus" ] ; then
            if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
                default_port="9095"
            else
                default_port="9090"
            fi
        elif [ "$daemon_type" = "grafana" ] ; then
            default_port="3000"
        elif [ "$daemon_type" = "alertmanager" ] ; then
            default_port="9093"
        elif [ "$daemon_type" = "node-exporter" ] ; then
            default_port="9100"
        else
            echo "_monitoring_smoke_test: extreme badness, bailing out!"
            false
        fi
        local nodes_arr
        local node_count
        node_count="0"
        local node_under_test
        local IFS
        local curl_exit_status
        IFS=","
        read -r -a nodes_arr <<<"$nodes_list"
        for (( n=0; n<${#nodes_arr[*]}; n++ )) ; do
            node_under_test="${nodes_arr[n]}"
            node_under_test="${node_under_test//[$'\t\r\n']}"
            _monitoring_wait_for "$daemon_type" "$node_under_test" "$default_port"
            true > "$temp_file"
            set -x
            set +e
            if [ "$ssl" ] ; then
                curl --silent --insecure "https://${node_under_test}:$default_port" | tee "$temp_file"
            else
                curl --silent "http://${node_under_test}:$default_port" | tee "$temp_file"
            fi
            curl_exit_status="${PIPESTATUS[0]}"
            set +x
            set -e
            if [ "$curl_exit_status" = "0" ] ; then
                if grep "$grep_for" "$temp_file" ; then
                    echo "curl output is OK for $daemon_type"
                    node_count="$((node_count + 1))"
                else
                    echo "BADNESS: curl output DOES NOT MATCH expected output for ${daemon_type}! Bailing out!"
                    false
                fi
            fi
        done
        echo "$daemon_type nodes expected/tested: $node_count/${#nodes_arr[*]}"
        if [ "$node_count" = "${#nodes_arr[*]}" ] ; then
            echo "WWWW: ${daemon_type}_smoke_test: OK"
            echo
        else
            echo "WWWW: ${daemon_type}_smoke_test: FAIL"
            echo
            false
        fi
    else
        echo "WWWW: ${daemon_type}_smoke_test: SKIPPED"
        echo
    fi
}

function prometheus_smoke_test {
    _monitoring_smoke_test "prometheus" "graph..Found"
}

function grafana_smoke_test {
    _monitoring_smoke_test "grafana" "title.Grafana" "ssl"
}

function alertmanager_smoke_test {
    _monitoring_smoke_test "alertmanager" "title.Alertmanager"
}

function node_exporter_smoke_test {
    _monitoring_smoke_test "node-exporter" "title.Node.Exporter"
}

function core_dump_test {
    local skipped
    local succeeded
    local osd_0_ps
    local osd_0_pid
    echo "WWWW: core_dump_test"
    if [ "$VERSION_ID" = "15.2" ] || [ "$ID" = "opensuse-tumbleweed" ] ; then
        echo "Asserting that there are no existing coredumps in the system."
        set -x
        coredumpctl list 2>&1 | grep 'No coredumps found'
        set +x
        echo "Looking for osd.0 on this node"
        set -x
        osd_0_ps="$(pgrep -a ceph-osd | grep osd\.0 | xargs)"
        set +x
        if [ "$osd_0_ps" ] ; then
            echo "Found \"pgrep\" line corresponding to osd.0:"
            echo "$osd_0_ps"
            osd_0_pid="${osd_0_ps%% *}"
            if [ "$osd_0_pid" ] ; then
                echo "Extracted PID of osd.0: $osd_0_pid"
                echo "Sending SIGSEGV to process $osd_0_pid"
                set -x
                kill -SEGV "$osd_0_pid"
                sleep 30
                coredumpctl list
                set +x
                if coredumpctl list 2>&1 | grep 'No coredumps found' ; then
                    echo "ERROR: no core dump collected"
                else
                    succeeded="yes"
                fi
            else
                echo "ERROR: could not extract PID from \"pgrep\" line?"
            fi
        else
            echo "osd.0 does not appear to be running on this node."
            skipped="yes"
        fi
    else
        echo "Test only works on recent SUSE OSes."
        skipped="yes"
    fi
    if [ "$skipped" ] ; then
        echo "core_dump_test: SKIPPED"
        echo
    elif [ "$succeeded" ] ; then
        echo "core_dump_test: OK"
        echo
    else
        echo "core_dump_test: FAIL"
        echo
        false
    fi
}
