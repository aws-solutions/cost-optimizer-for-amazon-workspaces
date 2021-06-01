FROM python:3.8.10

COPY ecs/workspaces_app.py /app/workspaces_app.py
COPY ecs /app/ecs

WORKDIR /app
RUN pip install boto3~=1.17.28
RUN pip install requests~=2.22.0
CMD python ./workspaces_app.py