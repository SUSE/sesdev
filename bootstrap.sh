#!/bin/bash

if [ -d ./sesdev ] ; then
    true
else
    >&2 echo "The working directory, $(pwd), does not look like a sesdev git clone."
    >&2 echo "Bailing out!"
    exit 1
fi

if type virtualenv > /dev/null 2>&1 ; then
    true
else
    >&2 echo "ERROR: virtualenv not available"
    >&2 echo "Please install the python3-virtualenv package for your OS, and try again."
    exit 1
fi

if [ -d ./venv ] ; then
    >&2 echo "Detected an existing virtual environment - blowing it away!"
    rm -rf ./venv
fi

virtualenv venv
source venv/bin/activate
pip install --editable .

>&2 echo
>&2 echo "sesdev installation complete."
>&2 echo "Remember to do \"source venv/bin/activate\" before trying to run sesdev!"
>&2 echo "When finished, issue the \"deactivate\" command to leave the Python virtual environment."
