# syntax=docker/dockerfile:1.4

FROM --platform=$TARGETPLATFORM python:latest

WORKDIR /usr/algalon

ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV OWNERID=$OWNERID

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "-u", "bot.py"]
