#!/bin/bash
set -eEuo pipefail

dir=$(dirname $(readlink -f ${0}))
esp32ToolchainFile="xtensa-esp32-elf-linux64-1.22.0-80-g6c4433a-5.2.0.tar.gz"
esp32ToolchainURL="https://dl.espressif.com/dl/${esp32ToolchainFile}"
espidfURL="https://github.com/espressif/esp-idf.git"
## Find out which hash is supported by running "make" in the micropython/ports/PORT dir
espidfHash="6ccb4cf5b7d1fdddb8c2492f9cbc926abaf230df"
micropythonGithub="https://github.com/micropython/micropython.git"
micropythonLibGithub="https://github.com/micropython/micropython-lib.git"
port="esp32"
portsModules="${dir}/micropython/ports/${port}/modules"

## Getting additional repos
echo "Initialising wlanProbe"
echo "Checking for micropython repo"
if [ ! -d "${dir}/micropython" ]; then
    git clone "${micropythonGithub}" "${dir}/micropython"
fi
echo "Checking for micropython-lib repo"
if [ ! -d "${dir}/micropython-lib" ]; then
    git clone "${micropythonLibGithub}" "${dir}/micropython-lib"
fi
echo "Checking for ESP-IDF repo"
if [ ! -d "${dir}/esp-idf" ]; then
    git clone "${espidfURL}" "${dir}/esp-idf"
    cd "${dir}/esp-idf"
    echo "Using supported esp-idf hash ${espidfHash}"
    git checkout "${espidfHash}"
    git submodule update --init --recursive
    cd - >> /dev/urandom
fi
echo "Getting the berkeley db lib for ESP32"
if [ ! -d "${dir}/micropython/lib/berkeley-db-1.xx/db" ]; then
    cd "${dir}/micropython"
    git submodule init lib/berkeley-db-1.xx
    git submodule update
    cd - >> /dev/urandom
fi

## Get the ESP32 toolchain
echo "Checking for ESP32 toolchain"
if [ ! -f "${dir}/micropythondev/${esp32ToolchainFile}" ]; then
    curl "${esp32ToolchainURL}" --output "${dir}/micropythondev/${esp32ToolchainFile}"
fi

## Some symlinks for libs we need for our Micropython project
echo "Setting up port ${port^^} with symlinks"
cd "${portsModules}"
if [ ! -L hashlib ]; then
    ln -s ../../../../micropython-lib/hashlib .
fi
if [ ! -L boot.py ]; then
    ln -s ../../../../wlanProbing.py boot.py
fi
cd - >> /dev/urandom

echo -e "Finished intialising the project\n"
echo "Do not forget to run 'make -C mpy-cross' in micropython dir in your development enviroment."
echo -e "Run 'startmicropythondev.sh' for a Docker based development environment.\n"
