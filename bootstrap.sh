#!/bin/bash

function abort_missing_dep {
    local executable="$1"
    local provided_by="$2"
    if type $executable > /dev/null 2>&1 ; then
        true
    else
        >&2 echo "ERROR: $executable not available"
        >&2 echo "Please install the $provided_by package for your OS, and try again."
        exit 1
    fi
}

if [ -d ./sesdev ] ; then
    true
else
    >&2 echo "The working directory, $(pwd), does not look like a sesdev git clone."
    >&2 echo "Bailing out!"
    exit 1
fi

abort_missing_dep python3 python3-base
abort_missing_dep virtualenv python3-virtualenv

if [ -d ./venv ] ; then
    >&2 echo "Detected an existing virtual environment - blowing it away!"
    rm -rf ./venv
fi

virtualenv --python=python3 venv
source venv/bin/activate
pip install --editable .

>&2 echo
>&2 echo "sesdev installation complete."
>&2 echo "Remember to do \"source venv/bin/activate\" before trying to run sesdev!"
>&2 echo "When finished, issue the \"deactivate\" command to leave the Python virtual environment."
