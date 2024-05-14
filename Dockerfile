# syntax=docker/dockerfile:1.4

FROM --platform=$TARGETPLATFORM python:3.12.3

WORKDIR /usr/algalon

COPY requirements.txt requirements.txt
RUN python3 -m pip install -U -r requirements.txt

COPY . .

CMD ["python", "-u", "bot.py"]
