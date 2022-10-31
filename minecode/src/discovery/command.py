#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import os
import signal
import subprocess

from discovery import ON_WINDOWS


logger = logging.getLogger(__name__)

# FIXME: use commoncode instead


class Command(object):
    """Simple wrapper around a subprocess."""

    def __init__(self, command, env=None, cwd=None):
        self.command = command
        self.env = env
        self.cwd = cwd or os.path.dirname(os.path.abspath(__file__))
        self.start()

    def start(self):
        self.proc = subprocess.Popen(self.command,
                                     shell=True,
                                     cwd=self.cwd,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     env=self.env,
                                     universal_newlines=True,
                                     close_fds=not ON_WINDOWS)
        self.returncode = self.proc.returncode

    def execute(self):
        return self.proc.stdout, self.proc.stderr

    def stop(self):
        if not self.proc:
            return

        close_pipe(getattr(self.proc, 'stdin', None))
        close_pipe(getattr(self.proc, 'stderr', None))
        close_pipe(getattr(self.proc, 'stdout', None))
        # Ensure process death in all cases, otherwise proc.wait seems to hang
        # in some cases

        def kill(sig, fun):
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
        signal.signal(signal.SIGALRM, kill)  # @UndefinedVariable
        signal.alarm(5)  # @UndefinedVariable

        # make sure the process is dead..
        self.proc.wait()
        self.proc = None


def close_pipe(pipe):
    if not pipe:
        return
    try:
        pipe.close()
    except IOError:
        pass
