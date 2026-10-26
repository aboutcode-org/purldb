.. _healthycode_metrics:

===========================
Healthycode health metrics
===========================

Metrics returned by Healthycode on ``GET /api/health/``. Adapted from
`METRICS.md <https://github.com/aboutcode-org/healthycode/blob/main/METRICS.md>`_
and the Healthycode JSON schema.

The HTTP 200 body has ``metrics``, plus ``score``, ``scoring_model``,
``commit_range``, ``run_start_date``, ``run_end_date``, ``purl``,
``source_purl``, ``vcs_url``, and ``date_collected``.

Organization for elephant factor and org counts comes from the commit
author email.

Score and commit range
----------------------

``score``
    Probability the repo is *unhealthy* (``0.0`` healthy .. ``1.0``
    unhealthy), from a logistic regression over the metrics.

``scoring_model``
    Model id, for example ``npm-health-0.2``.

``commit_range``
    ``first_commit``, ``last_commit``, ``first_commit_date``,
    ``last_commit_date`` for the analyzed window (Healthycode
    ``commitMetadata``). Any of these can be ``null``.

Activity
--------

``total_commits``
    Commits in the analyzed period.
    CHAOSS: `Code Changes Commits <https://www.chaoss.community/kb/metric-code-changes-commits/>`_.

``total_contributors``
    Unique people who made those commits.
    CHAOSS: `Contributors <https://www.chaoss.community/kb/metric-contributors/>`_.

``recent_commits``
    Commits in the last 90 days.

``recent_contributors``
    Unique people who committed in the last 90 days.

``active_branches``
    Branches with recent commits.
    CHAOSS: `Branch Lifecycle <https://www.chaoss.community/kb/metric-branch-lifecycle/>`_.

``days_since_last_commit``
    Days since the last commit. ``99999`` if there is no last-commit date.

Organizations and bus factor
----------------------------

``total_organizations``
    Distinct orgs that contributed in the analyzed period.
    CHAOSS: `Organizational Diversity <https://www.chaoss.community/kb/metric-organizational-diversity/>`_.

``recent_organizations``
    Distinct orgs that contributed in the last 90 days.

``pony_factor``
    How many people account for the first 50% of commits (sorted by volume).
    A low value means a few people carry the project. Also called lottery
    factor, bus factor, or contributor absence factor. Cutoff:
    ``pony_threshold`` (default 0.5).
    CHAOSS: `Contributor Absence Factor <https://www.chaoss.community/kb/metric-contributor-absence-factor/>`_.

``elephant_factor``
    Same idea as pony factor, but for organizations. Defined by Bitergia.
    Cutoff: ``elephant_threshold`` (default 0.5).
    CHAOSS: `Elephant Factor <https://www.chaoss.community/kb/metric-elephant-factor/>`_.

Contributor mix and growth
--------------------------

The analyzed period is split in two halves. Active contributors are people
with at least one commit in that half. Growth can be negative.

``contributor_growth``
    Second-half count minus first-half count.

    ::

        Growth(t1, t2) = Ca(t2) - Ca(t1)

``contributor_growth_rate``
    Growth divided by the first-half count.

    ::

        GrowthRate(t1, t2) = (Ca(t2) - Ca(t1)) / Ca(t1)

``developer_categories_core``, ``developer_categories_regular``, ``developer_categories_casual``
    Counts of core, regular, and casual contributors. Cutoffs are
    ``dev_categories_thresholds``: two cumulative commit-share values
    ``[core/regular, regular/casual]``.

``casual_regular_contributors_rate``
    Casual contributors divided by (core + regular).
    CHAOSS: `Occasional Contributors <https://www.chaoss.community/kb/metric-occasional-contributors/>`_.

``returning_contributors``
    People active in the last 90 days who also committed in an earlier
    period (retention).

Commit pace
-----------

``commits_over_periods_rate``
    Commits in the last 90 days relative to the last year. A rough sense
    of recent momentum.

``commits_per_week``, ``commits_per_month``, ``commits_per_year``
    Mean commits in that unit over the analyzed period. ``null`` if the
    period is shorter than 7, 30, or 365 days.

``coefficient_of_variation``
    Standard deviation of commits per month divided by the mean.

Files, diffs, and messages
--------------------------

File classes use ``code_file_pattern`` and ``binary_file_pattern``.

``file_types_code``, ``file_types_binary``, ``file_types_other``
    Touched files in each class. "Other" is everything that is not code
    or binary (docs, config, and so on).

``commit_size_added_lines``, ``commit_size_removed_lines``
    Lines added and removed.
    CHAOSS: `Change Request Commits <https://www.chaoss.community/kb/metric-change-request-commits/>`_.

``message_size_total``, ``message_size_mean``, ``message_size_median``
    Commit message length in characters (sum, mean, median).

Standard files
--------------

``found_file_license``
    ``1`` if ``LICENSE``, ``LICENSE.md``, ``LICENSE.txt``, or ``COPYING``
    is at the repo root, else ``0``.
    CHAOSS: `License Declared <https://www.chaoss.community/kb/metric-licenses-declared/>`_.

``found_file_adopters``
    ``1`` if ``ADOPTERS``, ``ADOPTERS.md``, or ``ADOPTERS.txt`` is at the
    repo root, else ``0``.

Healthycode run configuration
-----------------------------

Healthycode ``runMetadata.configuration`` is not always copied onto the
PurlDB response. When present it includes:

- ``from_date`` / ``to_date``: analysis window
- ``code_file_pattern`` / ``binary_file_pattern``: file class regexes
- ``pony_threshold`` / ``elephant_threshold``: commit-share cutoffs
- ``dev_categories_thresholds``: core / regular / casual cutoffs
