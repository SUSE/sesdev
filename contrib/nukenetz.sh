#!/bin/bash
#
# DISCLAIMER:
#
# This experimental script is full of sharp sticks that might hurt you if you
# don't know what you're doing, so if you have any doubts about it whatsoever,
# then don't use it!
#

INTERACTIVE="--interactive"
if [[ "$*" =~ "--non-interactive" ]] || [[ "$*" =~ "-f" ]] || [[ "$*" =~ "--force" ]]; then
    INTERACTIVE=""
fi

NETZ="$(sudo virsh net-list | egrep -v '\-\-\-|Persistent|vagrant-libvirt|^$' | cut -d' ' -f2)"
YES="non_empty_value"
if [ "$INTERACTIVE" ] ; then
    echo "Will nuke the following virtual networks:"
    for net in $NETZ ; do
        echo "- $net"
    done
    echo -en "Are you sure? (y/N) "
    read YES
    ynlc="${YES,,}"
    ynlcfc="${ynlc:0:1}"
    if [ -z "$YES" ] || [ "$yrlcfc" = "n" ] ; then
        YES=""
    else
        YES="non_empty_value"
    fi
fi

if [ "$YES" ] ; then
    for net in $NETZ ; do
        sudo virsh net-destroy $net
        sudo virsh net-undefine $net
    done
else
    echo "Aborting!"
fi
