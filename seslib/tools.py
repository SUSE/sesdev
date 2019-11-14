import fcntl
import logging
import os
import subprocess
import sys

from .exceptions import CmdException


logger = logging.getLogger(__name__)


def run_sync(command, cwd=None):
    logger.info("Running sync command (%s): %s", cwd if cwd else ".", command)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd) as proc:
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise CmdException(command, proc.returncode, stderr)
    return stdout.decode('utf-8')


def _non_block_read(fout):
    fd = fout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return fout.read()
    except Exception:
        return None


def run_async(command, callback, cwd=None):
    logger.info("Running async command (%s): %s", cwd if cwd else ".", command)
    callback("=== Running shell command ===\n{}\n".format(" ".join(command)))
    _command = ["stdbuf", "-oL"]
    _command.extend(command)
    with subprocess.Popen(_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=cwd) as proc:
        while True:
            output = _non_block_read(proc.stdout)
            if output:
                # got new output
                callback(output.decode('utf-8'))
            retcode = proc.poll()
            if retcode is not None:
                if retcode != 0:
                    raise CmdException(command, retcode, proc.stderr.read())
                break


def run_interactive(command, cwd=None):
    logger.info("Running interactive command (%s): %s", cwd if cwd else ".", command)
    r = subprocess.call(command, stdout=sys.stdout, stdin=sys.stdin)
    if r != 0:
        logger.warning("SSH interactive session finished with ret=%s", r)
    return r
