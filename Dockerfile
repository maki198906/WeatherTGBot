FROM python:3.9

WORKDIR /home

COPY requirements.txt ./
COPY *.py ./

ENV TELEGRAM_API_TOKEN=""
ENV OPEN_WEATHER_API_TOKEN=""

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "server.py"]
