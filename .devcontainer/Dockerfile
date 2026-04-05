# docker build -t mam10eks/trec-auto-judge-base:dev-0.0.1 . -f .devcontainer/Dockerfile
FROM ubuntu:jammy

RUN apt-get update \
	&& apt-get install -y git openjdk-17-jdk python3.11 python3-pip python3.11-dev

RUN python3.11 -m pip install uv 

ADD pyproject.toml /auto-judge/

WORKDIR /auto-judge

RUN apt-get install -y build-essential g++ gcc make python3-dev

RUN uv venv --python 3.11 /auto-judge/.venv \
	&& . /auto-judge/.venv/bin/activate \
	&& uv pip install -e .[all]

ENV PATH=/auto-judge/.venv/bin/:${PATH}

RUN python3 -c 'import nltk; nltk.download("stopwords"); nltk.download("punkt");'
