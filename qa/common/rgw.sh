#!/bin/bash
# This file is part of the sesdev-qa integration test suite

set -e

function install_rgw_test_dependencies {
    _zypper_ref_on_master
    _zypper_install_on_master curl libxml2-tools
}

function rgw_curl_test {
    local rgw_node="$1"
    local rgw_dns_name
    local rgw_frontends
    local port
    local protocol
    local curl_opts
    local rgwxmlout

    # Setup phase

    curl_opts=( --silent --show-error )

    # We are not currently testing RGW-over-HTTPS
    # test "$RGW_SSL" && protocol="https" || protocol="http"
    # test "$RGW_SSL" && curl_opts+=( --insecure )
    protocol="http"

    # If rgw_dns_name is configured, we must use it. Currently this is a problem
    # with {ses5,nautilus,ses6} only.
    rgw_dns_name="$(ceph-conf rgw_dns_name -s "client.rgw.$rgw_node" 2>/dev/null || true)"
    [ -z "$rgw_dns_name" ] && rgw_dns_name="$rgw_node"

    # The RGW port might be 80 or some other number.
    rgw_frontends="$(ceph-conf rgw_frontends -s "client.rgw.$rgw_node" 2>/dev/null || true)"
    [ "$rgw_frontends" ] && port="${rgw_frontends#*=}"
    echo "RGW port is ${port:=80}" >/dev/null

    rgwxmlout="/tmp/rgw_test.xml"

    # If RGW is running on the node, the following curl command will produce
    # valid XML containing the word "anonymous":

    # shellcheck disable=SC2086
    curl "${curl_opts[@]}" "${protocol}://${rgw_dns_name}:${port}" | tee $rgwxmlout

    # Testing phase
    test -f $rgwxmlout
    xmllint $rgwxmlout
    grep anonymous $rgwxmlout

    # Teardown phase
    rm -f $rgwxmlout
}
