PurlDB toolkit
==============

PurlDB is toolkit and library to use the PurlDB and its API.

The ``purlcli`` command acts as a client to the PurlDB REST API end point(s) to expose various
PURL services. It serves both as a tool, as a library and as an example on how to use the services
programmatically.

 
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
