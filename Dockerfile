# syntax=docker/dockerfile:1.4

FROM --platform=$TARGETPLATFORM python:3.11.6

WORKDIR /usr/algalon

COPY requirements.txt requirements.txt
RUN python3 -m pip install -U -r requirements.txt
RUN apt-get update && apt-get install -y nano

COPY . .

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
 CMD [ "sh" "-c" "[ -f /usr/algalon/health ]" ]

CMD ["python", "-u", "bot.py"]
