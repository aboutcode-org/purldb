matchcode-toolkit
=================
This contains a scancode-toolkit post-scan plugin that fingerprints the
directories of a scan and queries those fingerprints against the matchcode API
to find package matches.


Usage
-----

Ensure that the PurlDB server is up. Set the following environment variables:
  * ``MATCHCODE_DIRECTORY_CONTENT_MATCHING_ENDPOINT``

    * ``export MATCHCODE_DIRECTORY_CONTENT_MATCHING_ENDPOINT="http://127.0.0.1:8001/api/approximate_directory_content_index/match/"``

  * ``MATCHCODE_DIRECTORY_STRUCTURE_MATCHING_ENDPOINT``

    * ``export MATCHCODE_DIRECTORY_STRUCTURE_MATCHING_ENDPOINT="http://127.0.0.1:8001/api/approximate_directory_structure_index/match/"``

Install the matchcode-toolkit plugin into scancode-toolkit:
  * Open a shell and enable the virtual environment of the scancode-toolkit instance you want to use
  * Navigate to the matchcode-toolkit directory and run ``pip install -e .``

Run scancode with matching enabled:
  * The ``--info`` option has to be enabled on the scan you are running:

    * ``scancode --info --match <scan target directory> --json-pp -``

    or on the scan you are importing:

    * ``scancode --from-scan <path to scan JSON with --info> --match --json-pp -``
