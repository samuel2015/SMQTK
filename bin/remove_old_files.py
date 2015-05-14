#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monitor files under a given directory, removing them from dist after an expiry
period.
"""

import logging
import os
import time


sf_log = logging.getLogger("smqtk.scan_files")
is_log = logging.getLogger("smqtk.timed_scan")


def scan_files(base_dir, expire_seconds, action):
    """
    For files under the given starting directory, check the last access time
    against the expiry period (seconds) provided, applying action to that file
    path.

    :param base_dir: Starting directory for processing

    :param expire_seconds: Number of seconds since the last access of a file
        that should trigger the application of ``action``.

    :param action: Single argument function that will be given the path of a
        file that has not been accessed in ``expiry_seconds`` seconds.

    """
    for f in os.listdir(base_dir):
        f = os.path.join(base_dir, f)
        if os.path.isfile(f):
            s = os.stat(f)
            if time.time() - s.st_atime > expire_seconds:
                sf_log.debug("Action triggered for file: %s", f)
                action(f)
        elif os.path.isdir(f):
            scan_files(f, expire_seconds, action)
        else:
            raise RuntimeError("Encountered something not a file or directory? "
                               "Path: %s" % f)


def remove_file_action(filepath):
    os.remove(filepath)


def interval_scan(interval, base_dir, expire_seconds, action):
    """
    Action scan a directory every ``interval`` seconds. This will continue to
    run until the process is interrupted.

    :param interval: Number of seconds to wait in between each scan.

    :param base_dir: Starting directory for processing

    :param expire_seconds: Number of seconds since the last access of a file
        that should trigger the application of ``action``.

    :param action: Single argument function that will be given the path of a
        file that has not been accessed in ``expiry_seconds`` seconds.

    """
    while 1:
        is_log.debug("Starting scan on directory: %s", base_dir)
        scan_files(base_dir, expire_seconds, action)
        time.sleep(interval)


def main():
    from smqtk.utils.bin_utils import initializeLogging, SMQTKOptParser
    parser = SMQTKOptParser()
    parser.add_option('-d', '--base-dir',
                      help='Starting directory for scan.')
    parser.add_option('-i', '--interval', type=int,
                      help='Number of seconds between each scan (integer).')
    parser.add_option('-e', '--expiry', type=int,
                      help='Number of seconds until a file has "expired" '
                           '(integer).')
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='Display more messages (debugging).')
    opts, args = parser.parse_args()

    logging_level = logging.INFO
    if opts.verbose:
        logging_level = logging.DEBUG
    initializeLogging(logging.getLogger("smqtk"), logging_level)

    base_dir = opts.base_dir
    interval_seconds = opts.interval
    expiry_seconds = opts.expiry

    interval_scan(interval_seconds, base_dir, expiry_seconds,
                  remove_file_action)


if __name__ == '__main__':
    main()
