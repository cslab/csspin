FROM python:3.8-slim

# We'll need a git in here to get the package version number from git
# describe
RUN apt-get update \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools, as we'll install locked requirements first via
# pip-sync
RUN pip install pip-tools
ARG REQUIREMENTS
COPY $REQUIREMENTS /tmp/requirements.txt
RUN pip-sync /tmp/requirements.txt

# Install spin from this source tree
COPY . /spin
RUN pip install -q --no-deps --use-feature=in-tree-build /spin && rm -rf /spin
