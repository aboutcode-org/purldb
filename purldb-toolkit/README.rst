purldb-toolkit
==============

purldb-toolkit is command line utility and library to use the PurlDB, its API and various related libraries.

The ``purlcli`` command acts as a client to the PurlDB REST API end point(s) to expose PURL services.
It serves both as a tool, as a library and as an example on how to use the services programmatically.

 
Installation
------------

    pip install purldb-toolkit


Usage
-----

Use this command to get basic help::

    $ purlcli --help
    Usage: purlcli [OPTIONS] COMMAND [ARGS]...
    
      Return information from a PURL.
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      metadata  Given one or more PURLs, for each PURL, return a mapping of...
      urls      Given one or more PURLs, for each PURL, return a list of all...
      validate  Check the syntax of one or more PURLs.
      versions  Given one or more PURLs, return a list of all known versions...


And the following subcommands:

- Validate a PURL::

    $ purlcli validate --help
    Usage: purlcli validate [OPTIONS]
    
      Check the syntax of one or more PURLs.
    
    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write validation output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --help             Show this message and exit.


- Collect package versions for a PURL::
      
    $ purlcli versions  --help
    Usage: purlcli versions [OPTIONS]
    
      Given one or more PURLs, return a list of all known versions for each PURL.
    
      Version information is not needed in submitted PURLs and if included will be
      removed before processing.
    
    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write versions output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --help             Show this message and exit.


- Collect package metadata for a PURL::

    $ purlcli metadata --help
    Usage: purlcli metadata [OPTIONS]
    
      Given one or more PURLs, for each PURL, return a mapping of metadata fetched
      from the fetchcode package.py info() function.
    
    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write meta output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --unique           Return data only for unique PURLs.
      --help             Show this message and exit.


- Collect package URLs for a PURL::

    $ purlcli urls --help
    Usage: purlcli urls [OPTIONS]
    
      Given one or more PURLs, for each PURL, return a list of all known URLs
      fetched from the packageurl-python purl2url.py code.
    
    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write urls output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --unique           Return data only for unique PURLs.
      --head             Validate each URL's existence with a head request.
      --help             Show this message and exit.


Funding
-------

This project was funded through the NGI Assure Fund https://nlnet.nl/assure, a
fund established by NLnet https://nlnet.nl/ with financial support from the
European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 957073.

This project is also funded through grants from the Google Summer of Code
program, continuing support and sponsoring from nexB Inc. and generous
donations from multiple sponsors.


License
-------

Copyright (c) nexB Inc. and others. All rights reserved.

purldb is a trademark of nexB Inc.

SPDX-License-Identifier: Apache-2.0 AND CC-BY-SA-4.0

purldb software is licensed under the Apache License version 2.0.

purldb data is licensed collectively under CC-BY-SA-4.0.

See https://www.apache.org/licenses/LICENSE-2.0 for the license text.

See https://creativecommons.org/licenses/by-sa/4.0/legalcode for the license text.

See https://github.com/nexB/purldb for support or download.

See https://aboutcode.org for more information about nexB OSS projects.

