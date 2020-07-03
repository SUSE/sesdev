#!/bin/bash
# This file is part of the sesdev-qa integration test suite

set -e

function install_rgw_test_dependencies {
    _zypper_ref_on_master
    _zypper_install_on_master curl libxml2-tools
}

function rgw_curl_test {
    set +x
    local rgw_node="$1"
    local rgw_dns_name
    local rgw_frontends
    local port
    local protocol
    local curl_opts
    local curl_command
    local count
    local max_count_we_tolerate
    local rgwxmlout

    # Setup phase

    curl_command=( curl )
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

    curl_command+=( "${curl_opts[@]}" )
    curl_command+=( "${protocol}://${rgw_dns_name}:${port}" )
    count="0"
    max_count_we_tolerate="50"
    rgwxmlout="/tmp/rgw_test.xml"

    echo
    # shellcheck disable=SC2145
    echo "curl command for RGW ping \"${curl_command[@]}\""
    while true ; do
        count="$(( count + 1 ))"
        echo "Pinging RGW ($count/$max_count_we_tolerate) ..."
        set -x

        # If RGW is running on the node and is ready to serve requests, the
        # curl command will produce valid XML containing the word "anonymous":
        "${curl_command[@]}" | tee "$rgwxmlout"

        if [ "${PIPESTATUS[0]}" = "0" ] ; then
            set +x
            echo "RGW appears to be ready!"
            set -x
            break
        fi
        if [ "$count" = "$max_count_we_tolerate" ] ; then
            set +x
            echo "Exhausted all tries. Bailing out!"
            set -x
            exit 1
        fi
        sleep 5
    done

    # Testing phase
    test -s $rgwxmlout
    xmllint --format $rgwxmlout
    grep --quiet anonymous $rgwxmlout

    # Teardown phase
    rm -f $rgwxmlout
}
