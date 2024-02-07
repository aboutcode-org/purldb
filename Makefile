#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
VENV=venv
MANAGE=${VENV}/bin/python manage_purldb.py
MATCHCODE_MANAGE=${VENV}/bin/python manage_matchcode.py
ACTIVATE?=. ${VENV}/bin/activate;
VIRTUALENV_PYZ=../etc/thirdparty/virtualenv.pyz
# Do not depend on Python to generate the SECRET_KEY
GET_SECRET_KEY=`base64 /dev/urandom | head -c50`
# Customize with `$ make envfile ENV_FILE=/etc/purldb/.env`
ENV_FILE=.env
# Customize with `$ make postgres PACKAGEDB_DB_PASSWORD=YOUR_PASSWORD`
PACKAGEDB_DB_PASSWORD=packagedb
MATCHCODEIO_DB_PASSWORD=matchcodeio

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
	@./configure

dev:
	@echo "-> Configure and install development dependencies"
	@./configure --dev

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}

envfile_testing:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" >> ${ENV_FILE}
	@echo SCANCODEIO_DB_PORT=\"5433\" >> ${ENV_FILE}

isort:
	@echo "-> Apply isort changes to ensure proper imports ordering"
	${VENV}/bin/isort .

black:
	@echo "-> Apply black code formatter"
	${VENV}/bin/black .

doc8:
	@echo "-> Run doc8 validation"
	@${ACTIVATE} doc8 --max-line-length 100 --ignore-path docs/_build/ --quiet docs/

valid: isort black

check:
	@echo "-> Run pycodestyle (PEP8) validation"
	@${ACTIVATE} pycodestyle --max-line-length=100 --exclude=venv,lib,thirdparty,docs,migrations,settings.py .
	@echo "-> Run isort imports ordering validation"
	@${ACTIVATE} isort --check-only .
	@echo "-> Run black validation"
	@${ACTIVATE} black --check ${BLACK_ARGS}

clean:
	@echo "-> Clean the Python env"
	@./configure --clean

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

postgres_matchcodeio:
	@echo "-> Configure PostgreSQL database"
	@echo "-> Create database user 'matchcodeio'"
	${SUDO_POSTGRES} createuser --no-createrole --no-superuser --login --inherit --createdb matchcodeio || true
	${SUDO_POSTGRES} psql -c "alter user matchcodeio with encrypted password '${MATCHCODEIO_DB_PASSWORD}';" || true
	@echo "-> Drop 'matchcodeio' database"
	${SUDO_POSTGRES} dropdb matchcodeio || true
	@echo "-> Create 'matchcodeio' database"
	${SUDO_POSTGRES} createdb --encoding=utf-8 --owner=matchcodeio matchcodeio
	${MATCHCODE_MANAGE} migrate

run:
	${MANAGE} runserver 8001 --insecure

run_matchcodeio:
	${MATCHCODE_MANAGE} runserver 8002 --insecure

seed:
	${MANAGE} seed

run_visit: seed
	${MANAGE} run_visit --ignore-robots --ignore-throttle

run_map:
	${MANAGE} run_map

request_scans:
	${MANAGE} request_scans

process_scans:
	${MANAGE} process_scans

test:
	@echo "-> Run the test suite"
	${ACTIVATE} DJANGO_SETTINGS_MODULE=purldb_project.settings ${PYTHON_EXE} -m pytest -vvs --ignore matchcode-toolkit --ignore matchcode_pipeline --ignore matchcode_project --ignore purldb-toolkit --ignore packagedb/tests/test_throttling.py
	${ACTIVATE} DJANGO_SETTINGS_MODULE=purldb_project.settings ${PYTHON_EXE} -m pytest -vvs packagedb/tests/test_throttling.py
	${ACTIVATE} DJANGO_SETTINGS_MODULE=matchcode_project.settings ${PYTHON_EXE} -m pytest -vvs matchcode_pipeline
	${ACTIVATE} ${PYTHON_EXE} -m pytest -vvs matchcode-toolkit --ignore matchcode-toolkit/src/matchcode_toolkit/pipelines
	${ACTIVATE} ${PYTHON_EXE} -m pytest -vvs purldb-toolkit

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
	@${ACTIVATE} sphinx-build docs/ docs/_build/

docker-images:
	@echo "-> Build Docker services"
	docker-compose build
	@echo "-> Pull service images"
	docker-compose pull
	@echo "-> Save the service images to a compressed tar archive in the dist/ directory"
	@mkdir -p dist/
	@docker save minecode minecode_minecode nginx | gzip > dist/minecode-images-`git describe --tags`.tar.gz

.PHONY: virtualenv conf dev envfile isort black doc8 valid check clean migrate postgres run test shell clearsync clearindex index_packages bump docs docker-images
