Changelog
=========

next-next-next-release (2022-XX-XX)
-----------------------------------
 * Bump dependency versions
    * Update Django to 4.0.4
    * Update djangorestframework to 3.13.1
    * Update django-filter to 21.1
    * Update packagedb to 1.2.3
    * Update psycopg2 to 2.9.3
  * Use django.utils.translation.gettext_lazy instead of django.utils.translation.ugettext_lazy
  * Use django.urls.re_path instead of django.conf.urls.url

next-next-release (2021-XX-XX)
------------------------------

 * Remove MatchRequest and Match models and APIs from matchcode. Matchcode will provide API
   access to the different matching indices and return results for individual
   fingerprint lookups instead of running the matching process on the entire
   codebase of Resources at once.
 * Reorganize fingerprinting, indexing, and matching functions into their own files.
 * Modify matching functions and tests to work without the MatchRequest and Match models.
   These functions will go into a scanpipe pipes/pipeline later.

next-release (2021-XX-XX)
-------------------------

 * Improved approximate directory structure and approximate directory content
   matching available through API
 * We now return exact directory matches, if available. If no exact match is found,
   the closest matches are returned.
 * Package matches are placed in top-level ``packages`` field in JSON results.
   Package matches are related to files using the purl of a package.
 * Show stats when the command index_packages is done running
 * Send match completion notifications via webhooks. MatchRequest API now
   accepts webhook URLs during creation.
 * Delay running matching task for 10 seconds after a MatchRequest is received.
   This is to ensure that the received MatchRequest is written to the database before being used.
 * The field `indexed_elements_count` has been added to `BaseDirectoryIndex`.
   `indexed_elements_count` is an integer that represents the number of inputs used to create the
   fingerprint. During a match, a fingerprint is compared to other fingerprints whose size is
   within 5% of our fingerprints size.
 * File size is now used in the creation of ApproximateDirectoryStructureIndex fingerprints.

v0.0.1 (201X-XX-XX)
-------------------

 * Initial release
 * SHA1 Package matching available through API (``api/match_request``)
 * label, uuid, created_date, task_start_date, task_end_date, status,
   execution_time, input_scan, and match_results for a given match request
   available through API
