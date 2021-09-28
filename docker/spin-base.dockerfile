FROM python:3.8-slim
RUN pip install pip-tools
ARG REQUIREMENTS
COPY $REQUIREMENTS /tmp/requirements.txt
RUN pip-sync /tmp/requirements.txt
COPY . /spin
RUN pip install -q --no-deps --no-build-isolation --use-feature=in-tree-build /spin && rm -rf /spin
