FROM ubuntu:jammy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN <<EOF
set -e
apt-get update
apt-get install -y git python3-dev build-essential
EOF

COPY pyproject.toml /tmp/stub/pyproject.toml

# Install only the dependencies declared in pyproject.toml (not the project itself)
RUN uv pip install --system '/tmp/stub[all]' && uv pip uninstall --system auto-judge-starterkit

ENV OPENAI_BASE_URL=does-not-exist
ENV OPENAI_MODEL=does-not-exist
ENV OPENAI_API_KEY=does-not-exist