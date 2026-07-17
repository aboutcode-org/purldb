#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import datetime
from unittest.mock import patch

from packagedb.schedules import get_next_execution


def test_get_next_execution():
    time_now = datetime.datetime(
        2024,
        1,
        1,
        0,
        tzinfo=datetime.timezone.utc,
    )

    watch_interval_days1 = 2
    last_watch_date1 = None
    expected1 = time_now

    watch_interval_days2 = 2
    last_watch_date2 = time_now
    expected2 = datetime.datetime(
        2024,
        1,
        3,
        0,
        tzinfo=datetime.timezone.utc,
    )

    with patch("datetime.datetime", wraps=datetime.datetime) as dt:
        dt.now.return_value = time_now

        assert expected1 == get_next_execution(watch_interval_days1, last_watch_date1)
        assert expected2 == get_next_execution(watch_interval_days2, last_watch_date2)
