# syntax=docker/dockerfile:1.4

FROM --platform=$TARGETPLATFORM python:latest

WORKDIR /usr/algalon

COPY requirements.txt requirements.txt
RUN python3 -m pip install -U -r requirements.txt
RUN apt-get update && apt-get install -y nano

COPY . .

CMD ["python", "-u", "bot.py"]
