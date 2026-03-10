# GitHub Actions Self-Hosted Runner
# Usage: docker compose -f infrastructure/actions-runner/docker-compose.runner.yml up -d --build

FROM ubuntu:22.04

ARG RUNNER_VERSION=2.332.0
ARG RUNNER_ARCH=x64

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    jq \
    python3 \
    python3-pip \
    docker.io \
    make \
    sudo \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 -s /bin/bash runner \
  && usermod -aG docker runner \
  && echo "runner ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/runner \
  && chmod 0440 /etc/sudoers.d/runner

WORKDIR /actions-runner

RUN curl -fsSL \
      "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz" \
      -o runner.tar.gz \
  && tar xzf runner.tar.gz \
  && rm runner.tar.gz \
  && ./bin/installdependencies.sh

COPY entrypoint.sh /actions-runner/entrypoint.sh
RUN chmod +x /actions-runner/entrypoint.sh \
  && chown -R runner:runner /actions-runner

USER runner

ENTRYPOINT ["/actions-runner/entrypoint.sh"]
