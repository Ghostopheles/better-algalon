# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM python:3.10.2

WORKDIR /usr/algalon

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "-u", "bot.py"]
