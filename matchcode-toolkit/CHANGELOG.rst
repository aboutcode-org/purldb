Changelog
=========

v3.0.0
------

*2024-02-23* -- Update ``ScanAndFingerprintPackage`` pipeline to reflect the renaming of the ``ScanPackage`` pipeline to ``ScanSinglePackage`` in scancode.io

v2.0.1
------

*2023-12-19* -- Update ``ScanAndFingerprintPackage`` pipeline with updates from the upstream ``ScanPackage`` pipeline from scancode.io

v2.0.0
------

*2023-12-18* -- Remove ``ScanAndFingerprintPackage`` pipeline from matchcode-toolkit's entry points. (https://github.com/nexB/purldb/issues/263)

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
