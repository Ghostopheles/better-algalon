# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM python:3.11.1-bullseye

WORKDIR /usr/algalon

ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV OWNERID=$OWNERID

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "-u", "bot.py"]
