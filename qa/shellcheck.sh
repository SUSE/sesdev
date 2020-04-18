#!/bin/bash

# set -x

SCRIPTS_TO_SHELLCHECK="shellcheck.sh
health-ok.sh
common/common.sh
common/helper.sh
common/json.sh
common/zypper.sh
"

function abort_missing_dep {
    local executable="$1"
    local provided_by="$2"
    if type "$executable" > /dev/null 2>&1 ; then
        true
    else
        >&2 echo "ERROR: $executable not available"
        >&2 echo "Please install the $provided_by package for your OS, and try again."
        exit 1
    fi
}

function run_shellcheck_on {
    local target="$1"
    shellcheck "$target"
}

abort_missing_dep shellcheck ShellCheck

if [ -e "./health-ok.sh" ] ; then
    true
else
    >&2 echo "ERROR: not in the qa/ directory"
    exit 1
fi

for script in $SCRIPTS_TO_SHELLCHECK ; do
    run_shellcheck_on "$script"
done

