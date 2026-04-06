FROM ubuntu:24.04

# gcc-ia16 cross-compiler for 16-bit x86 targets
# Used to compile Doom8088 for x86CSS

RUN apt-get update && \
    apt-get install -y software-properties-common gpg && \
    add-apt-repository -y ppa:tkchia/build-ia16 && \
    apt-get update && \
    apt-get install -y \
        gcc-ia16-elf \
        libi86-ia16-elf \
        nasm \
        make \
        python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
