# temporary builder image for wireguard tools
# - need coherent system version with base image
# - may need update for properly compiling boringtun (eg: cargo build package failing on `buster-slim`)
FROM debian:bullseye-slim as builder

RUN apt-get update && apt-get install -y git build-essential curl

# install boringtun userspace implementation of wireguard
# 
# - match versions of debian & boringtun : 0.4.0 is now supported by bullseye with current system/cargo packages
#   0.5.2 not yet supported
# - glitch: bullseye's apt-get cargo is too old vs boringtun's cargo packages dependencies, need to install
#   up to date rust/cargo
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y && . /root/.cargo/env && \
    cargo install --locked --bin boringtun --version ~0.4.0 boringtun

# install needed wireguard-tools
ENV WITH_WGQUICK=yes
RUN git clone https://git.zx2c4.com/wireguard-tools && \
    make -C wireguard-tools/src && \
    make -C wireguard-tools/src install


# docker base image for VPN server, Fed-BioMed node and researcher
# - need proper python version for Fed-BioMed
FROM python:3.9-slim-bullseye

RUN apt-get update && apt-get install -y iptables iproute2 iputils-ping bash vim net-tools procps build-essential kmod

# get wireguard from builder image
COPY --from=builder /root/.cargo/bin/boringtun /usr/bin/
COPY --from=builder /usr/bin/wg* /usr/bin/
