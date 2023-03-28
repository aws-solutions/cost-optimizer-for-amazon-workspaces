FROM public.ecr.aws/docker/library/python:3.10.10-slim-bullseye
COPY workspaces_app /workspaces_app

WORKDIR /workspaces_app

RUN pip install -r ./setup_requirements.txt
RUN pip install -r ./requirements.txt

CMD python3 ./main.py
