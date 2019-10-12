#!/bin/bash
set -eEuo pipefail

micropythonGithub="https://github.com/micropython/micropython.git"
micropythonLibGithub="https://github.com/micropython/micropython-lib.git"
esp32ToolchainFile="xtensa-esp32-elf-linux64-1.22.0-80-g6c4433a-5.2.0.tar.gz"
esp32ToolchainURL="https://dl.espressif.com/dl/${esp32ToolchainFile}"

echo "Initialising wlanProbe"
echo "Checking for micropython repo"
if [ ! -d micropython ]; then
    /usr/bin/git clone "${micropythonGithub}" micropython
fi
echo "Checking for micropython-lib repo"
if [ ! -d micropython-lib ]; then
    /usr/bin/git clone "${micropythonLibGithub}" micropython-lib
fi
echo "Checking for ESP32 toolchain"
if [ ! -f "micropythondev/${esp32ToolchainFile}" ]; then
    /usr/bin/curl "${esp32ToolchainURL}" --output "micropythondev/${esp32ToolchainFile}"
fi
echo "Finished intialising the project"
