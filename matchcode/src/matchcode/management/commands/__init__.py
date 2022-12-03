#
# Copyright (c) 2017 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

import logging

from django.core.management.base import BaseCommand


class VerboseCommand(BaseCommand):
    """
    Base verbosity-aware Command.
    Command modules should define logging and subclasses should call
       logger.setLevel(self.get_verbosity(**options))
    in their handle() method.
    """

    def get_verbosity(self, **options):
        verbosity = int(options.get('verbosity', 1))
        levels = {1: logging.INFO, 2: logging.ERROR, 3: logging.DEBUG}
        return levels.get(verbosity, logging.CRITICAL)

    MUST_STOP = False

    @classmethod
    def stop_handler(cls, *args, **kwargs):
        """
        Signal handler use to support a graceful exit when flag is to True.
        Subclasses must create this signal to use this:
            signal.signal(signal.SIGTERM, Command.stop_handler)
        """
        cls.MUST_STOP = True
