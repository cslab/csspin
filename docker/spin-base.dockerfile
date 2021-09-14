FROM python:3.8-slim
RUN pip install pip-tools
COPY requirements.txt .
RUN pip-sync requirements.txt
COPY . /spin
RUN pip install -q --no-deps --use-feature=in-tree-build /spin && rm -rf /spin
