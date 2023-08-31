Changelog
=========

v1.1.3
------

*2023-08-31* -- Do not fingerprint empty directories.
*2023-08-31* -- Track fingerprints to ignore in ``matchcode_toolkit.fingerprinting.IGNORED_DIRECTORY_FINGERPRINTS``.

v1.1.2
------

*2023-08-02* -- Update ``scan_and_fingerprint_package`` pipeline to use new directory fingerprinting functions from scancode.io.

v1.1.1
------

*2023-06-29* -- Do not include empty files when computing directory fingerprints.

v1.1.0
------

*2023-06-22* -- Rename ``compute_directory_fingerprints`` to ``compute_codebase_directory_fingerprints`` and create a new version of ``compute_directory_fingerprints`` that works on Resource objects instead of codebases.

v1.0.0
------

*2023-06-05* -- Initial release.
