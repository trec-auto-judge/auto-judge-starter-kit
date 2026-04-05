# The base image is build from 
FROM mam10eks/trec-auto-judge-base:dev-0.0.1

RUN . /auto-judge/.venv/bin/activate \
	&& python3 -m spacy download en_core_web_sm \
	&& python3 -c 'from tira.third_party_integrations import ensure_pyterrier_is_loaded; ensure_pyterrier_is_loaded(patch_ir_datasets=True, is_offline=False)' \
	&& python3 -c 'from language_tool_python import LanguageTool; LanguageTool(language="en-US")'

ADD judges /auto-judge/judges
ADD pyproject.toml /auto-judge/

ENV PYTHONPATH=/auto-judge

ENV HF_HUB_OFFLINE=1

