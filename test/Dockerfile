

## run in app root dir:
## 1. docker build -t smlmqttprocessortest -f test/Dockerfile
## 2. docker run --rm -ti --name smlmqttprocessortest smlmqttprocessortest

## https://hub.docker.com/_/python
FROM python:3.5-slim

## https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
ENV VIRTUAL_ENV=/app/venv

WORKDIR /app

COPY requirements.txt ./
RUN python3 -m venv $VIRTUAL_ENV \
    && . $VIRTUAL_ENV/bin/activate \
    && python3 -m pip install --no-cache-dir -r requirements.txt

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY . .

CMD [ "python", "-m", "pytest" ]
