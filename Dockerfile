# syntax=docker/dockerfile:1.4

ARG BUILDPLATFORM
ARG TARGETPLATFORM

FROM --platform=$BUILDPLATFORM python:latest

WORKDIR /usr/algalon

ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV OWNERID=$OWNERID

COPY requirements.txt requirements.txt
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt

COPY . .

CMD ["python", "-u", "bot.py"]
