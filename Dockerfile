# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM python:3.10.2
#--platform=linux/arm/v7 python:3.10.2

WORKDIR /usr/algalon

ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV OWNERID=$OWNERID

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD ["python3", "-u", "bot.py"]
