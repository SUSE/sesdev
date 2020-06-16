#!/bin/bash
#
# integration test automation script "health-ok.sh"
#

set -e
trap 'catch $?' EXIT

SCRIPTNAME="$(basename "${0}")"
BASEDIR="$(readlink -f "$(dirname "${0}")")"
test -d "$BASEDIR"
# [[ $BASEDIR =~ \/sesdev-qa$ ]]

# shellcheck disable=SC1091
source /etc/os-release
# shellcheck disable=SC1090
# shellcheck disable=SC1091
source "$BASEDIR/common/common.sh"

function catch {
    echo
    echo -n "Overall result: "
    if [ "$1" = "0" ] ; then
        echo "OK"
    else
        echo "NOT_OK (error $2)"
    fi
}

function usage {
    echo "$SCRIPTNAME - script for testing HEALTH_OK deployment"
    echo "for use in SUSE Enterprise Storage testing"
    echo
    echo "Usage:"
    echo "  $SCRIPTNAME [-h,--help] [--igw=X] [--mds=X] [--mgr=X]"
    echo "  [--mon=X] [--nfs=X] [--strict-versions] [--rgw=X]"
    echo "  [--total-nodes=X]"
    echo
    echo "Options:"
    echo "    --help               Display this usage message"
    echo "    --igw-nodes          expected number of nodes with iSCSI Gateway"
    echo "    --mds-nodes          expected number of nodes with MDS"
    echo "    --mgr-nodes          expected number of nodes with MGR"
    echo "    --mon-nodes          expected number of nodes with MON"
    echo "    --nfs-nodes          expected number of nodes with NFS"
    echo "    --osd-nodes          expected number of nodes with OSD"
    echo "    --igw-node-list      comma-separated list of nodes with iSCSI Gateway"
    echo "    --mds-node-list      comma-separated list of nodes with MDS"
    echo "    --mgr-node-list      comma-separated list of nodes with MGR"
    echo "    --mon-node-list      comma-separated list of nodes with MON"
    echo "    --nfs-node-list      comma-separated list of nodes with NFS"
    echo "    --osd-node-list      comma-separated list of nodes with OSD"
    echo "    --osds               expected total number of OSDs in cluster"
    echo "    --strict-versions    Insist that daemon versions match \"ceph --version\""
    echo "    --rgw-nodes          expected number of nodes with RGW"
    echo "    --total-nodes        expected total number of nodes in cluster"
    exit 1
}

assert_enhanced_getopt

TEMP=$(getopt -o h \
--long "help,igw-nodes:,mds-nodes:,mgr-nodes:,mon-nodes:,nfs-nodes:,osd-nodes:,osds:,strict-versions,rgw-nodes:,total-nodes:" \
-n 'health-ok.sh' -- "$@") || ( echo "Terminating..." >&2 ; exit 1 )
eval set -- "$TEMP"

# set some global variables
ADMIN_KEYRING="/etc/ceph/ceph.client.admin.keyring"
CEPH_CONF="/etc/ceph/ceph.conf"
IGW_NODES=""
IGW_NODE_LIST=""
MDS_NODES=""
MDS_NODE_LIST=""
MGR_NODES=""
MGR_NODE_LIST=""
MON_NODES=""
MON_NODE_LIST=""
NFS_NODES=""
NFS_NODE_LIST=""
OSD_NODES=""
OSD_NODE_LIST=""
RGW_NODES=""
RGW_NODE_LIST=""
OSDS=""
STRICT_VERSIONS=""
TOTAL_NODES=""

# process command-line options
while true ; do
    case "$1" in
        --igw-nodes) shift ; IGW_NODES="$1" ; shift ;;
        --igw-node-list) shift ; IGW_NODE_LIST="$1" ; shift ;;
        --mds-nodes) shift ; MDS_NODES="$1" ; shift ;;
        --mds-node-list) shift ; MDS_NODE_LIST="$1" ; shift ;;
        --mgr-nodes) shift ; MGR_NODES="$1" ; shift ;;
        --mgr-node-list) shift ; MGR_NODE_LIST="$1" ; shift ;;
        --mon-nodes) shift ; MON_NODES="$1" ; shift ;;
        --mon-node-list) shift ; MON_NODE_LIST="$1" ; shift ;;
        --nfs-nodes) shift ; NFS_NODES="$1" ; shift ;;
        --nfs-node-list) shift ; NFS_NODE_LIST="$1" ; shift ;;
        --osd-nodes) shift ; OSD_NODES="$1" ; shift ;;
        --osd-node-list) shift ; OSD_NODE_LIST="$1" ; shift ;;
        --rgw-nodes) shift ; RGW_NODES="$1" ; shift ;;
        --rgw-node-list) shift ; RGW_NODE_LIST="$1" ; shift ;;
        --osds) shift ; OSDS="$1" ; shift ;;
        --strict-versions) STRICT_VERSIONS="$1"; shift ;;
        --total-nodes) shift ; TOTAL_NODES="$1" ; shift ;;
        -h|--help) usage ;;    # does not return
        --) shift ; break ;;
        *) echo "Internal error" ; exit 1 ;;
    esac
done

# use all global variables once to avoid SC2034
set +e
test "$ADMIN_KEYRING"
test "$CEPH_CONF"
test "$IGW_NODES"
test "$MDS_NODES"
test "$MGR_NODES"
test "$MON_NODES"
test "$NFS_NODES"
test "$OSD_NODES"
test "$RGW_NODES"
test "$IGW_NODE_LIST"
test "$MDS_NODE_LIST"
test "$MGR_NODE_LIST"
test "$MON_NODE_LIST"
test "$NFS_NODE_LIST"
test "$OSD_NODE_LIST"
test "$RGW_NODE_LIST"
test "$OSDS"
test "$STRICT_VERSIONS"
test "$TOTAL_NODES"
set -e

# run tests
support_cop_out_test
no_non_oss_repos_test
make_salt_master_an_admin_node_test
ceph_rpm_version_test
ceph_cluster_running_test
ceph_daemon_versions_test "$STRICT_VERSIONS"
mgr_is_available_test
maybe_wait_for_osd_nodes_test "$OSD_NODES"  # it might take a long time for OSD nodes to show up
maybe_wait_for_mdss_test "$MDS_NODES"  # it might take a long time for MDSs to be ready
maybe_wait_for_rgws_test "$RGW_NODES"  # it might take a long time for RGWs to be ready
maybe_wait_for_nfss_test "$NFS_NODES"  # it might take a long time for NFSs to be ready
number_of_daemons_expected_vs_metadata_test
number_of_services_expected_vs_orch_ls_test
number_of_services_expected_vs_orch_ps_test
number_of_daemons_expected_vs_actual
ceph_health_test
