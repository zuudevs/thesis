#!/usr/bin/env python3
"""ssh-remote-saq — non-interactive remote exec + file transfer to the SAQ server.

Usage:
    python scripts/ssh-remote-saq/ssh-remote.py run "<remote command>" [--timeout N]
    python scripts/ssh-remote-saq/ssh-remote.py push <local> <remote>
    python scripts/ssh-remote-saq/ssh-remote.py pull <remote> <local>
    python scripts/ssh-remote-saq/ssh-remote.py smoke

Credentials: scripts/ssh-remote-saq/.env (gitignored) with SSH_SAQ_NAME /
SSH_SAQ_HOST / SSH_SAQ_PASS. The remote is Windows OpenSSH (default shell
cmd.exe); remote paths use forward slashes (e.g. D:/SKRIPSI/RAFI/sources).

Design notes (audit ND-6 / AUD-1):
- NON-interactive by design: the previous version launched an interactive
  `powershell` over ssh with no pseudo-TTY and hung forever (reproduced:
  subprocess.TimeoutExpired). Every remote command here must terminate.
- The remote command is passed as ONE plain string with NO extra quoting
  layer — subprocess on Windows re-quotes list arguments, and embedded
  quotes double-wrap.
- StrictHostKeyChecking=accept-new pins the host key on first contact
  (replaces `no`, which disabled verification entirely).
- sshpass feeds the password for now; the follow-up is key-based auth
  (Windows admin users install the public key into
  C:/ProgramData/ssh/administrators_authorized_keys, not ~/.ssh).
- scp on this server runs in legacy (cmd-based) mode: REMOTE paths must be
  HOME-RELATIVE (e.g. `ze_probe.tmp` lands in C:/Users/Admin/). Absolute
  drive-letter remote specs (`admin@host:C:/...`) fail with "The system
  cannot find the path specified." — for an absolute destination, scp to a
  home-relative name first, then `run` a move/copy.
"""

import argparse
import subprocess
import threading
from os import getenv
from pathlib import Path
from subprocess import Popen, run
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / '.env'
SSH_OPTS = ['-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=10']
SMOKE_CMD = 'whoami & node --version & git --version & hostname'


def load_creds():
    load_dotenv(ENV_PATH)
    name, host, pw = getenv('SSH_SAQ_NAME'), getenv('SSH_SAQ_HOST'), getenv('SSH_SAQ_PASS')
    if not (name and host and pw):
        raise SystemExit(f'missing credentials in {ENV_PATH} (see .env.example)')
    return f'{name}@{host}', pw


def run_remote(cmd, timeout=None):
    """Stream a non-interactive remote command; return the ssh exit code."""
    host, pw = load_creds()
    args = ['sshpass', '-p', pw, 'ssh', *SSH_OPTS, host, cmd]
    proc = Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                 text=True, encoding='utf-8', errors='replace')
    watchdog = threading.Timer(timeout, proc.kill) if timeout else None
    if watchdog:
        watchdog.start()
    try:
        for line in proc.stdout:
            print(line, end='')
        proc.wait()
    finally:
        if watchdog:
            watchdog.cancel()
    return proc.returncode if proc.returncode is not None else 124


def transfer(direction, src, dst):
    """scp upload/download; remote paths use forward slashes."""
    host, pw = load_creds()

    def as_remote(p):
        return p if '@' in p or ':' in p else f'{host}:{p}'

    if direction == 'push':
        pair = (src, as_remote(dst))
    else:
        pair = (as_remote(src), dst)
    result = run(['sshpass', '-p', pw, 'scp', *SSH_OPTS, *pair])
    return result.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run', help='run a non-interactive remote command')
    r.add_argument('command')
    r.add_argument('--timeout', type=int, default=None,
                   help='kill the remote session after N seconds (exit 124)')
    p = sub.add_parser('push', help='scp upload (forward slashes in remote paths)')
    p.add_argument('src')
    p.add_argument('dst')
    l = sub.add_parser('pull', help='scp download (forward slashes in remote paths)')
    l.add_argument('src')
    l.add_argument('dst')
    sub.add_parser('smoke', help='connectivity + remote toolchain probe')
    a = ap.parse_args()
    if a.cmd == 'run':
        return run_remote(a.command, a.timeout)
    if a.cmd == 'push':
        return transfer('push', a.src, a.dst)
    if a.cmd == 'pull':
        return transfer('pull', a.src, a.dst)
    return run_remote(SMOKE_CMD)


if __name__ == '__main__':
    raise SystemExit(main())
