#!/bin/bash
set -eEuo pipefail


init() {
    if [ "${#}" == "0" ]; then
        runEpoch=$(/bin/date +%s)
    else
        # Force Docker image build with any parameter
        runEpoch=32503680000
    fi
    # This is a week
    maxImageAge=604801
    dir=$(dirname $(readlink -f ${0}))
    week=$(/bin/date +%Y%m%V)
    dockerRun="/usr/bin/sudo /usr/bin/docker run --interactive=true --tty=true --volume=${dir}:/data"
    dockerImage="micropythondev:${week}"
    devicesList="/dev/ttyACM0 /dev/ttyUSB0 /dev/ttyUSB1"
    devicesRun=""
    envPort=""
    
    
    for i in ${devicesList}; do
        if [ -e ${i} ]; then
            devicesRun="${devicesRun}--device=${i} "
        envPort="${envPort}--env PORT=${i} "
        fi
    done
    }


imageCheck() {
    inImageName=${1}
    imageCreatedReal=$(imageInspect ${inImageName})
    imageCreatedEpoch=$(/bin/date +%s --date="${imageCreatedReal}")
    let imageAge=${runEpoch}-${imageCreatedEpoch## }
    if [ "${imageAge}" -gt "${maxImageAge}" ]; then
        echo "Build"
    else
        echo "NoBuild"
    fi
    }


imageInspect() {
    inImageName=${1}
    if /usr/bin/sudo /usr/bin/docker image inspect ${inImageName} >/dev/null 2>&1; then
        lastTagTime=$(/usr/bin/sudo /usr/bin/docker image inspect ${inImageName} --format "{{.Metadata.LastTagTime}}")
        echo -n "${lastTagTime%%.*}"
    else
        echo -n "1970-01-01T00:00:00.000000000Z"
    fi
    }    


main() {
    init "${@}"
    mpdAge=$(imageCheck ${dockerImage})
    if [ "${mpdAge}" == "Build" ]; then
        echo "Building fresh MicroPython image"
        cd micropythondev
        ./build.sh
        cd -
    fi
    dockerExec="${dockerRun} ${envPort}${devicesRun}${dockerImage}"
    exec ${dockerExec}
}

main "${@}"
