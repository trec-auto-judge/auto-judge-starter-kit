# The base image is build from https://github.com/OpenWebSearch/wows-code/blob/main/ecir26/template-new-approach/Dockerfile.dev
FROM ghcr.io/openwebsearch/wows-code/ecir-2026-pyterrier:latest

RUN apt-get update \
	&& apt-get install -y git openjdk-11-jdk python3 python3-pip

RUN pip3 install uv

ADD judges /auto-judge/judges
ADD pyproject.toml /auto-judge/

WORKDIR /auto-judge

RUN uv pip install --system -e .

