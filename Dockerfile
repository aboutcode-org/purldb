# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

FROM --platform=linux/amd64 python:3.9

WORKDIR /app

# Python settings: Force unbuffered stdout and stderr (i.e. they are flushed to terminal immediately)
ENV PYTHONUNBUFFERED 1
# Python settings: do not write pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
       bzip2 \
       xz-utils \
       zlib1g \
       libxml2-dev \
       libxslt1-dev \
       libpopt0 \
       bzip2 \
       tar \
       unzip \
       zip \
       libsasl2-dev \
       libldap-dev \
       openssl \
       wait-for-it \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY setup.cfg setup.py /app/
RUN mkdir -p /app/matchcode-toolkit/src/
COPY matchcode-toolkit/setup.cfg matchcode-toolkit/setup.py /app/matchcode-toolkit/
RUN pip install -e matchcode-toolkit
RUN pip install -e .

COPY . /app
