FROM python:3.7.3

COPY wco.py /app/wco.py
COPY lib /app/lib

WORKDIR /app
RUN pip install --upgrade pip
RUN pip install boto3

CMD python ./wco.py
