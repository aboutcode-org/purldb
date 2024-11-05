Matchcode
==========

MatchCode.io
------------

MatchCode.io is a Django app, based off of ScanCode.io, that exposes one API
endpoint, ``api/matching``, which takes a ScanCode.io codebase scan, and
performs Package matching on it.

Currently, it performs three matching steps:

  * Match codebase resources against the Packages in the PackageDB
  * Match codebase resources against the Resources in the PackageDB
  * Match codebase directories against the directory matching indices of
    MatchCode


MatchCode.io API Endpoints
--------------------------

* ``api/matching``

  * Performs Package matching on an uploaded ScanCode.io scan
  * Intended to be used with the ``match_to_purldb`` pipeline in ScanCode.io


Docker Setup for Local Development and Testing
----------------------------------------------

PurlDB and MatchCode.io are two separate Django apps. In order to run both of
these Django apps on the same host, we need to use Traefik.

Traefik is an edge router that receives requests and finds out which services
are responsible for handling them. In the docker-compose.yml files for PurlDB
and MatchCode.io, we have made these two services part of the same Docker
network and set up the routes for each service.

All requests to the host go to the PurlDB service, but requests that go to the
``api/matching`` endpoint are routed to the MatchCode.io service.

To run PurlDB and Matchcode.io with Docker:
::

  docker compose -f docker-compose.yml up -d
  docker compose -f docker-compose.matchcodeio.yml up -d

Scancode.io pipeline
---------------------

ScanCode.io pipeline: :ref:`scancode.io:pipeline_match_to_matchcode`

Refer to the scancode.io documentation about the matchcode add-on pipeline
which matches the codebase resources of a project against MatchCode.io to
identify packages, creating DiscoveredPackages from these and assigning
codebase resources to it.

.. toctree::
   :maxdepth: 2

   matchcode-pipeline
