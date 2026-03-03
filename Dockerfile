FROM python:3.12-slim

WORKDIR /home

COPY requirements.txt ./
COPY *.py ./

ARG TELEGRAM
ARG OPEN_WEATHER

ENV TELEGRAM_API_TOKEN=$TELEGRAM
ENV OPEN_WEATHER_API_TOKEN=$OPEN_WEATHER

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "server.py"]
