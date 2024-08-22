# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

FROM --platform=linux/amd64 python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/aboutcode-org/purldb"
LABEL org.opencontainers.image.description="PurlDB"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV APP_NAME purldb
ENV APP_USER app
ENV APP_DIR /opt/$APP_NAME
ENV VENV_LOCATION /opt/$APP_NAME/venv

# Force Python unbuffered stdout and stderr (they are flushed to terminal immediately)
ENV PYTHONUNBUFFERED 1
# Do not write Python .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Add the app dir in the Python path for entry points availability
ENV PYTHONPATH $PYTHONPATH:$APP_DIR

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
       bzip2 \
       xz-utils \
       zlib1g \
       libxml2-dev \
       libxslt1-dev \
       libgomp1 \
       libsqlite3-0 \
       libgcrypt20 \
       libpopt0 \
       libzstd1 \
       libgpgme11 \
       libdevmapper1.02.1 \
       libguestfs-tools \
       linux-image-amd64 \
       git \
       wait-for-it \
       universal-ctags \
       gettext \
       tar \
       unzip \
       zip \
       libsasl2-dev \
       libldap-dev \
       openssl \
       cvs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create the APP_USER group and user
RUN addgroup --system $APP_USER \
 && adduser --system --group --home=$APP_DIR $APP_USER \
 && chown $APP_USER:$APP_USER $APP_DIR

# Create the /var/APP_NAME directory with proper permission for APP_USER
RUN mkdir -p /var/$APP_NAME \
 && chown $APP_USER:$APP_USER /var/$APP_NAME \
 && mkdir -p /var/scancodeio \
 && chown $APP_USER:$APP_USER /var/scancodeio

# Setup the work directory and the user as APP_USER for the remaining stages
WORKDIR $APP_DIR
USER $APP_USER

# Create the virtualenv
RUN python -m venv $VENV_LOCATION
# Enable the virtualenv, similar effect as "source activate"
ENV PATH $VENV_LOCATION/bin:$PATH

# Create static/ and workspace/ directories
RUN mkdir -p /var/$APP_NAME/static/ \
 && mkdir -p /var/$APP_NAME/workspace/ \
 && mkdir -p /var/scancodeio/static/ \
 && mkdir -p /var/scancodeio/workspace/

# Install the dependencies before the codebase COPY for proper Docker layer caching
COPY --chown=$APP_USER:$APP_USER setup.cfg setup.py $APP_DIR/
RUN pip install --no-cache-dir .

# Copy the codebase and set the proper permissions for the APP_USER
COPY --chown=$APP_USER:$APP_USER . $APP_DIR
