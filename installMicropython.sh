#!/bin/bash
set -eEuo pipefail

/home/user/esp32py/bin/esptool.py --chip esp32 --port ${PORT} write_flash -z 0x1000 ${1}
