FROM python:3.9

WORKDIR /home

COPY requirements.txt ./
COPY *.py ./

ENV TELEGRAM_API_TOKEN="5189011185:AAGDFFJ1BrOCMTQf4u6sbQgOanRo7You-iM"
ENV OPEN_WEATHER_API_TOKEN="284defe8cfc3fa926097b2a09ca2fcde"

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "server.py"]
