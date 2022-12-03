#!/usr/bin/env python
#
# Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
#

import os
import sys


if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchcodeio.settings')
    execute_from_command_line(sys.argv)
