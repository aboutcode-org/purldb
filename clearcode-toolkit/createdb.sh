#!/bin/bash
# Copyright (c) nexB Inc. and others. All rights reserved.

echo "-> Create the ClearCode database"

# CREATEDB is required for clearcode in order to run tests in the future
sudo -u postgres psql <<EOF
CREATE ROLE clearcode PASSWORD 'cl34-u5er' NOSUPERUSER NOCREATEROLE INHERIT LOGIN CREATEDB;
CREATE DATABASE clearcode WITH OWNER=clearcode TEMPLATE=template0 ENCODING='UTF8' LC_COLLATE='en_US.utf8 ' LC_CTYPE='en_US.utf8';
EOF
