# syntax=docker/dockerfile:1.7

FROM mcr.microsoft.com/devcontainers/go:1-1.23-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/home/vscode/.local/bin:${PATH}"

RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash-completion \
        build-essential \
        curl \
        fd-find \
        jq \
        less \
        make \
        pkg-config \
        ripgrep \
        shellcheck \
        sqlite3 \
        tree \
        unzip \
        xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && if [ -x /usr/bin/fdfind ] && [ ! -e /usr/local/bin/fd ]; then ln -s /usr/bin/fdfind /usr/local/bin/fd; fi \
    && mkdir -p /home/vscode/.local/bin /home/vscode/.local/share \
    && chown -R vscode:vscode /home/vscode/.local
