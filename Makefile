#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
VENV=venv
MANAGE=${VENV}/bin/python manage.py
ACTIVATE?=. ${VENV}/bin/activate;
VIRTUALENV_PYZ=../etc/thirdparty/virtualenv.pyz
# Do not depend on Python to generate the SECRET_KEY
GET_SECRET_KEY=`base64 /dev/urandom | head -c50`

# Customize with `$ make envfile ENV_FILE=/etc/purldb/.env`
ENV_FILE=.env

# Customize with `$ make postgres PACKAGEDB_DB_PASSWORD=YOUR_PASSWORD`
PACKAGEDB_DB_PASSWORD=packagedb

# Django settings shortcuts
DJSM_PDB=DJANGO_SETTINGS_MODULE=purldb.settings

# Use sudo for postgres, but only on Linux
UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	SUDO_POSTGRES=sudo -u postgres
else
	SUDO_POSTGRES=
endif

virtualenv:
	@echo "-> Bootstrap the virtualenv with PYTHON_EXE=${PYTHON_EXE}"
	@${PYTHON_EXE} ${VIRTUALENV_PYZ} --never-download --no-periodic-update ${VENV}

conf:
	@echo "-> Install dependencies"
	@PYTHON_EXECUTABLE=${PYTHON_EXE} ./configure

dev:
	@echo "-> Configure and install development dependencies"
	@PYTHON_EXECUTABLE=${PYTHON_EXE} ./configure --dev

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}

envfile_testing: envfile
	@echo PACKAGEDB_DB_USER=\"postgres\" >> ${ENV_FILE}
	@echo PACKAGEDB_DB_PASSWORD=\"postgres\" >> ${ENV_FILE}

doc8:
	@echo "-> Run doc8 validation"
	@${ACTIVATE} doc8 --quiet docs/ *.rst

valid:
	@echo "-> Run Ruff format"
	@${ACTIVATE} ruff format
	@echo "-> Run Ruff linter"
	@${ACTIVATE} ruff check --fix

check:
	@echo "-> Run Ruff linter validation (pycodestyle, bandit, isort, and more)"
	@${ACTIVATE} ruff check
	@echo "-> Run Ruff format validation"
	@${ACTIVATE} ruff format --check
	@$(MAKE) doc8
	@echo "-> Run ABOUT files validation"
	@${ACTIVATE} about check etc/

clean:
	@echo "-> Clean the Python env"
	@PYTHON_EXECUTABLE=${PYTHON_EXE} ./configure --clean
	rm -rf .venv/ .*cache/ *.egg-info/ build/ dist/
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

migrate:
	@echo "-> Apply database migrations"
	${MANAGE} migrate

postgres:
	@echo "-> Configure PostgreSQL database"
	@echo "-> Create database user 'packagedb'"
	${SUDO_POSTGRES} createuser --no-createrole --no-superuser --login --inherit --createdb packagedb || true
	${SUDO_POSTGRES} psql -c "alter user packagedb with encrypted password '${PACKAGEDB_DB_PASSWORD}';" || true
	@echo "-> Drop 'packagedb' database"
	${SUDO_POSTGRES} dropdb packagedb || true
	@echo "-> Create 'packagedb' database"
	${SUDO_POSTGRES} createdb --encoding=utf-8 --owner=packagedb packagedb
	@$(MAKE) migrate

run:
	${MANAGE} runserver 8001 --insecure

seed:
	${MANAGE} seed

run_visit: seed
	${MANAGE} run_visit --ignore-robots --ignore-throttle

run_map:
	${MANAGE} run_map

test_purldb:
	${ACTIVATE} ${DJSM_PDB} pytest -vvs --lf minecode matchcode packagedb purl2vcs purldb clearcode clearindex --ignore minecode/tests/pipes --ignore packagedb/tests/test_throttling.py
	${ACTIVATE} ${DJSM_PDB} pytest -vvs --lf packagedb/tests/test_throttling.py

test_minecode_pipelines:
	${ACTIVATE} ${DJSM_PDB} pytest -vvs --lf minecode/tests/pipes

test: test_purldb test_minecode_pipelines

shell:
	${MANAGE} shell

clearsync:
	${MANAGE} clearsync --save-to-db --verbose -n 3

clearindex:
	${MANAGE} run_clearindex

index_packages:
	${MANAGE} index_packages

priority_queue:
	${MANAGE} priority_queue

bump:
	@echo "-> Bump the version"
	bin/bumpver update --no-fetch --patch

docs:
	rm -rf docs/_build/
	@${ACTIVATE} sphinx-build docs/source docs/_build/

docs-check:
	@${ACTIVATE} sphinx-build -E -W -b html docs/source docs/_build/
	@${ACTIVATE} sphinx-build -E -W -b linkcheck docs/source docs/_build/

docker-images:
	@echo "-> Build Docker services"
	docker-compose build
	@echo "-> Pull service images"
	docker-compose pull
	@echo "-> Save the service images to a compressed tar archive in the dist/ directory"
	@mkdir -p dist/
	@docker save minecode minecode_minecode nginx | gzip > dist/minecode-images-`git describe --tags`.tar.gz

# keep this sorted
.PHONY: bump check docs-check clean clearindex clearsync conf dev docker-images docs envfile envfile_testing index_packages migrate postgres priority_queue run run_map run_visit seed shell test test_purldb test_minecode_pipelines valid virtualenv
