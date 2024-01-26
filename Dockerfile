FROM python:3.10-slim
WORKDIR /app
RUN apt-get update
RUN apt-get -y install libpq-dev gcc
COPY bot/requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
