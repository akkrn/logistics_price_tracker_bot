FROM python:3.10-slim
WORKDIR /app
RUN apt-get update
RUN apt-get -y install libpq-dev gcc
RUN pip install --no-cache-dir -r ./bot/requirements.txt