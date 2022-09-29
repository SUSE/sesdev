import fcntl
import os
import random
import re
import string
import subprocess
import sys
import time
from urllib.parse import urlparse
from typing import Tuple

import requests

from .exceptions import CmdException
from .log import Log


def is_a_glob(a_string):
    """
    Return True or False depending on whether a_string appears to be a glob
    """
    if isinstance(a_string, str):
        pattern = re.compile(r'[\*\[\]\{\}\?]')
        return bool(pattern.search(a_string))
    return False


def run_sync(command, cwd=None):
    Log.info("Running sync command in directory {}: {}"
             .format(cwd if cwd else ".", command)
            )
    with subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          cwd=cwd,
                          shell=False) as proc:
        (stdout, stderr) = proc.communicate()
        if proc.returncode != 0:
            raise CmdException(command, proc.returncode, stderr)
    return stdout.decode('utf-8')


def _non_block_read(fout):
    # pylint: disable=invalid-name
    fd = fout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return fout.read()
    except Exception:  # pylint: disable=broad-except
        return None


def run_async(command, callback, cwd=None):
    Log.info("Running async command in directory {}: {}"
             .format(cwd if cwd else ".", command)
            )
    callback("=== Running shell command ===\n{}\n".format(" ".join(command)))
    _command = ["stdbuf", "-oL"]
    _command.extend(command)
    with subprocess.Popen(_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=cwd) as proc:
        while True:
            time.sleep(0.5)
            output = _non_block_read(proc.stdout)
            if output:
                # got new output
                callback(output.decode('utf-8'))
            retcode = proc.poll()
            if retcode is not None:
                if retcode != 0:
                    raise CmdException(command, retcode, proc.stderr.read().decode('utf-8'))
                break


def run_interactive(command, cwd=None):
    Log.info("Running interactive command in directory {}: {}"
             .format(cwd if cwd else ".", command)
            )
    ret = subprocess.call(command, stdout=sys.stdout, stdin=sys.stdin)
    if ret != 0:
        Log.warning("SSH interactive session finished with ret={}".format(ret))
    return ret


def gen_random_string(length):
    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str.lower()


def image_manifest_exists(image_url: str) -> Tuple[bool, requests.Response]:
    def container_path_to_manifest_url(container_path: str) -> str:
        tag = "latest"
        if re.search(r":(\w+)$", container_path):
            container_path, tag = container_path.rsplit(":", 1)
        url = urlparse(f"https://{container_path}")
        return f"{url.scheme}://{url.netloc}/v2{url.path}/manifests/{tag}"

    url = container_path_to_manifest_url(image_url)
    resp = requests.head(url, verify=False, timeout=10)
    return resp.status_code == 200, resp
