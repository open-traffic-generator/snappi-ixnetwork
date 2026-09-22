#!/bin/sh

if [ -z ${1} ]; then
    PYTHON=python
else
    PYTHON=${1}
fi

rm -rf .venv
${PYTHON} -m pip install --upgrade virtualenv \
&& ${PYTHON} -m virtualenv .venv \
&& .venv/bin/python -m pip install --upgrade -r requirements.txt \
&& .venv/bin/python -m pip install --upgrade -e ".[dev]"
