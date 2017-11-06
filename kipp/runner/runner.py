#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
-----------
Kipp Runner
-----------

Collect scripts' running status into MongoDB

Arguments:
    -t, --timeout (int): seconds to throw ``KippRunnerTimeoutException``
    -l, --lock: only allow single process running

Examples:
::
    cd code/postconvertor && TARS_ENV=www2 /opt/venv/bin/python -m kipp.runner -t 30 -l "/opt/venv/bin/python PostConvertor.py"
"""

from __future__ import unicode_literals

import argparse
import subprocess
import sys
import inspect
import time
import os
import signal
import traceback
from datetime import timedelta
from random import randint
from textwrap import dedent

from kipp.options import options as opt
opt.patch_utilities()

from kipp.aio import Event, run_until_complete
from kipp.libs.aio import KippAIOTimeoutError
from kipp.utils import (ThreadPoolExecutor, check_is_allow_to_running,
                        generate_validate_fname, get_logger, EmailSender, utcnow)

from .exceptions import KippRunnerTimeoutException, KippRunnerException, KippRunnerSIGTERMException
from .models import RunStatsMonitor


RECEIVERS = (
    'lcai@movoto.com',
)


def is_need_to_clean_old_records():
    return randint(0, 1000) == 1


def clean_monitor_logs():
    dt_range = timedelta(days=-30)
    if is_need_to_clean_old_records():
        opt.runner_monitor.clean_logs_by_timedelta(dt_range)


def _process_runner(process, evt):
    def _set_evt(futu):
        evt.set()

    f = opt.executor.submit(process.communicate)
    f.add_done_callback(_set_evt)
    return f


def kill_process(process):
    if not process:
        return

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except OSError:
        pass


def send_alert_email(msg):
    get_logger().info('try to send runner alert email...')
    if opt.debug:
        receivers = 'lcai@movoto.com'
    else:
        receivers = ','.join(RECEIVERS)

    content = dedent('''
        time: {dt}
        command: {command}
        error: {err}
        '''.format(dt=utcnow().strftime('%Y-%m-%dT%H:%M:%S'), command=opt.command, err=msg))

    opt.sender.send_email(
        mail_from='data@movoto.com',
        mail_to=receivers,
        subject='DATA Monitoring: Runner got critical error',
        content=content
    )


def wait_process_done(process, timeout):
    evt = Event()
    f_p = _process_runner(process, evt)
    try:
        futu = evt.wait(timeout=opt.timeout)
        run_until_complete(futu)
        futu.result()
    except KippAIOTimeoutError:
        try:
            kill_process(process)
        except OSError:
            return f_p.result()
        else:
            raise KippRunnerTimeoutException('process exceeds timeout {}s'.format(timeout))
    else:
        return f_p.result()
    finally:
        opt.executor.shutdown()


def handle_signal_quit(signal, frame):
    err_msg = 'quit by signal {}:\n{}'.format(signal, inspect.getframeinfo(frame))
    if signal:
        raise KippRunnerSIGTERMException(err_msg)


def catch_sys_quit_signal():
    signal.signal(signal.SIGTERM, handle_signal_quit)


def runner(command):
    process = err_msg = None
    opt.set_option('runner_command_start_at', time.time())
    try:
        opt.set_option('runner_monitor', RunStatsMonitor(command=command, args=sys.argv[1: -1]))
        clean_monitor_logs()
        catch_sys_quit_signal()
        opt.runner_monitor.start()
        get_logger().info('kipp.runner for %s', command)
        opt.set_option('runner_command_start_at', time.time())  # override start_at before real process starting
        process = subprocess.Popen([command], shell=True, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        if opt.timeout:
            r = wait_process_done(process, opt.timeout)
        else:
            r = process.communicate()

        if process.returncode != 0:
            err_msg = r[1]
            raise RuntimeError(err_msg)
    except BaseException as err:
        get_logger().exception(err)
        err_msg = traceback.format_exc()
        opt.runner_monitor.fail(err_msg)
        # Not send email in kipp.runner
        # if time.time() - opt.runner_command_start_at < opt.minimal_running_seconds:
        #     send_alert_email(err_msg)

        raise
    else:
        get_logger().info('successed: %s', command)
        opt.runner_monitor.success()
    finally:
        kill_process(process)


def setup_settings():
    opt.set_option('executor', ThreadPoolExecutor(2))
    opt.set_option('sender', EmailSender(host=opt.SMTP_HOST))


def setup_arguments():
    opt.add_argument('-t', '--timeout', type=int, default=0, help='seconds')
    opt.add_argument('-ms', '--minimal_running_seconds', type=int, default=30, help='minimal running seconds')
    opt.add_argument('-l', '--lock', action='store_true', default=False, help='only allow single running')
    opt.add_argument('--debug', action='store_true', default=False)
    opt.add_argument('command', nargs=argparse.REMAINDER)
    opt.parse_args()
    if not opt.command:
        raise AttributeError('You should run like ``python -m runner <COMMAND>``')

    opt.set_option('command', ' '.join(opt.command))


def main():
    setup_arguments()
    setup_settings()

    if opt.lock:
        lock_fname = generate_validate_fname(opt.command)
        fp = check_is_allow_to_running(lock_fname)
        if not fp:
            raise KippRunnerException('another process is still running')

    runner(opt.command)
