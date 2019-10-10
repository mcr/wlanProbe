#!/bin/bash
set -eEuo pipefail

devicesList="/dev/ttyACM0 /dev/ttyUSB0 /dev/ttyUSB1"

if [ ${#} == 0 ]; then
    for i in ${devicesList}; do
        if [ -e ${i} ]; then
            serialDevice=${i}
	    break
        fi
    done
else
    case "${1}" in
        1) 
            serialDevice="/dev/ttyACM0"
	    ;;
        2) 
	    serialDevice="/dev/ttyUSB0"
	    ;;
        3)
            serialDevice="/dev/ttyUSB1"
	    ;;
	*)
	    echo "This is not the device you are looking for"
	    echo "1: /dev/ttyACM0
	          2: /dev/ttyUSB0
		  3: /dev/ttyUSB1"
	    ;;
    esac
fi
/usr/bin/picocom --baud=115200 "${serialDevice}"
exit "${?}"
