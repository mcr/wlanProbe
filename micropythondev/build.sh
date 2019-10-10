#!/bin/bash
set -eEuo pipefail

dir=$(dirname ${0})
week=$(date +%Y%m%V)

cd ${dir}
/usr/bin/sudo /usr/bin/docker build --pull --tag micropythondev:${week} .
cd -
