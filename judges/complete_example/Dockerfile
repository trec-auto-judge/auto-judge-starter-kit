FROM ubuntu:jammy

RUN apt-get update \
	&& apt-get install -y git python3 python3-pip

RUN pip3 install uv

# Install main package from git + local extras
RUN uv pip install --system git+https://github.com/trec-auto-judge/auto-judge-starter-kit.git \
	&& uv pip install --system tqdm \
	&& uv pip install --system ir-datasets

ENV OPENAI_BASE_URL=does-not-exist
ENV OPENAI_MODEL=does-not-exist
ENV OPENAI_API_KEY=does-not-exist

COPY example_judge.py /naive-baseline.py