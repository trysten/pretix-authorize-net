FROM debian:buster

RUN apt-get update && \
    apt-get install --no-install-recommends --assume-yes \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libenchant1c2a \
    gettext \
    git \
    build-essential \
    wget

RUN python3 -m pip install --upgrade pip setuptools wheel

RUN wget https://raw.githubusercontent.com/pretix/pretix/master/src/requirements/dev.txt && \
    #wget https://raw.githubusercontent.com/pretix/pretix/master/src/requirements/production.txt && \
    pip3 install -r dev.txt # -r production.txt

RUN pip3 install pretix

#It's a bad idea to cache the migrations, do anyway
RUN /usr/local/bin/pretix migrate

COPY .  /opt/app
