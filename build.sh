#!/bin/sh

if [ -f .settings.sh ]
then
    . ./.settings.sh
fi

if [ -z "$MICROPYTHON" ] || [ -z "$TARGET" ]
then
    echo "Please set MICROPYTHON= directory with micropython build"
    echo "Please set TARGET=      board type (within ports/)"
    echo Current values are:
    echo MICROPYTHON=$MICROPYTHON
    echo TARGET=$TARGET
    echo Please also set variables for micropython.
    exit 1

fi

# make build directory fully-qualified
HERE=$(pwd)
BUILD=$HERE/build-${TARGET}

mkdir -p $BUILD
make -C $MICROPYTHON/ports/$TARGET FROZEN_MPY_DIR=${HERE}/py FLASH_MODE=dio PORT=${PORT} $*
#make -C $MICROPYTHON/ports/$TARGET BUILD=$BUILD FROZEN_MPY_DIR=${HERE}/py PORT=${PORT} FLASH_MODE=dio $*
#make -C $MICROPYTHON/ports/$TARGET BUILD=$BUILD FLASH_MODE=dio $*

