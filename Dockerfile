# syntax=docker/dockerfile:1

FROM --platform=linux/arm/v7 python:3.10.2

WORKDIR /usr/algalon

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

ENTRYPOINT ["python", "-u", "bot.py"]
