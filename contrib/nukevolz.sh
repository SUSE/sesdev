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

VOLZ="$(sudo virsh vol-list default | egrep -v '\-\-\-|Name|^$' | cut -d' ' -f2)"
if [ -z "$VOLZ" ] ; then
    echo "No volumes to nuke"
    exit 0
fi
YES="non_empty_value"
if [ "$INTERACTIVE" ] ; then
    echo "Will nuke the following volumes:"
    for vol in $VOLZ ; do
        echo "- $vol"
    done
    echo -en "Are you sure? (y/N) "
    read -r YES
    ynlc="${YES,,}"
    ynlcfc="${ynlc:0:1}"
    if [ -z "$YES" ] || [ "$ynlcfc" = "n" ] ; then
        YES=""
    else
        YES="non_empty_value"
    fi
fi

if [ "$YES" ] ; then
    for vol in $VOLZ ; do
        sudo virsh vol-delete --pool default "$vol"
    done
    rm -rf "~/.vagrant.d/boxes/*"
else
    echo "Aborting!"
fi
