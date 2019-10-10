FROM ubuntu:19.04

#Get it from https://dl.espressif.com/dl/xtensa-esp32-elf-linux64-1.22.0-80-g6c4433a-5.2.0.tar.gz
ARG toolchain=xtensa-esp32-elf-linux64-1.22.0-80-g6c4433a-5.2.0.tar.gz

RUN /usr/bin/apt-get update && \
    /usr/bin/apt-get dist-upgrade --yes && \
    /usr/bin/apt-get autoremove --purge --yes && \
    /usr/bin/apt-get install --yes \
        less \
        python2 \
        python3 \
        vim \
        tmux \
	virtualenv \
        build-essential \
        libreadline-dev \
        libffi-dev \
        git \
        pkg-config \
        gcc-arm-none-eabi \
        libnewlib-arm-none-eabi \
	gcc \
        git \
        wget \
        make \
        libncurses-dev \
        flex \
        bison \
        gperf 

RUN /usr/sbin/addgroup --quiet --gid 1000 user && \
    /usr/sbin/useradd --shell /bin/bash --uid 1000 --gid 1000 --create-home user && \
    /usr/sbin/usermod --append --groups dialout user

RUN /bin/mkdir /data && /bin/chown 1000:1000 -R /data

USER 1000

RUN /bin/mkdir /home/user/esp32Toolchain

ADD ${toolchain} /home/user/esp32Toolchain

RUN echo '\nPATH="${HOME}/esp32Toolchain/xtensa-esp32-elf/bin:${PATH}"' >> /home/user/.bashrc && \
    echo 'export PATH' >> /home/user/.bashrc && \
    echo '\nESPIDF="/data/esp-idf"' >> /home/user/.bashrc && \
    echo 'export ESPIDF="/data/esp-idf"' >> /home/user/.bashrc

RUN /usr/bin/virtualenv --python=/usr/bin/python3 /home/user/esp32py && \
    /home/user/esp32py/bin/pip install adafruit-ampy cryptography esptool future pyparsing && \
    echo "\nsource /home/user/esp32py/bin/activate" >> /home/user/.bashrc

WORKDIR /data

ENTRYPOINT ["/bin/bash"]
