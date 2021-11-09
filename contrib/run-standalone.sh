#!/bin/bash
#
# run sesdev test script "contrib/standalone.sh" while leveraging
# GNU script to capture all output in a file called "typescript"
#
SCRIPTNAME="$(basename "$0")"
BASEDIR="$(readlink -f "$(dirname "$0")")"
COMMAND="$BASEDIR/standalone.sh $* ; exit"
script -c "$COMMAND"
