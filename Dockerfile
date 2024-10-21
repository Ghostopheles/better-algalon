# syntax=docker/dockerfile:1.4-labs

FROM --platform=$TARGETPLATFORM python:3.12.3

WORKDIR /algalon

RUN pip install -U pip
RUN pip install -U setuptools

RUN apt-get update
RUN apt-get install -y curl build-essential libssl-dev libffi-dev python3-dev cargo

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt requirements.txt
RUN pip install -U -r requirements.txt

COPY . .

CMD ["python", "-u", "main.py"]
