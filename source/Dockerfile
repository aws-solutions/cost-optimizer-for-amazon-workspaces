FROM python:3.9.13-slim-buster

COPY workspaces_app /workspaces_app

WORKDIR /workspaces_app

RUN pip install -r ./setup_requirements.txt
RUN pip install -r ./requirements.txt

CMD python3 ./main.py
