# syntax=docker/dockerfile:1.4

FROM --platform=$TARGETPLATFORM python:latest

WORKDIR /usr/algalon

COPY requirements.txt requirements.txt
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt

COPY . .

CMD ["python", "-u", "bot.py"]
