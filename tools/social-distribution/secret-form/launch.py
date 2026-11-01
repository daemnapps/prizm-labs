"""Keep the temporary receiver/tunnel alive independently of the chat turn."""
import os
from pathlib import Path
import signal
import subprocess
import sys

here = Path(__file__).resolve().parent
out = here.parents[2] / 'output' / 'geelark'
out.mkdir(parents=True, exist_ok=True)
if '--run' not in sys.argv:
    with open(out / 'receiver.log', 'a') as log:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--run'],
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    (out / 'supervisor.pid').write_text(str(child.pid))
    print('Temporary connection started.')
else:
    receiver = subprocess.Popen([sys.executable, str(here / 'server.py')], stdin=subprocess.DEVNULL)
    with open(out / 'tunnel.log', 'w') as log:
        tunnel = subprocess.Popen(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'IdentityFile=/dev/null', '-o', 'ConnectTimeout=15', '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'UserKnownHostsFile=' + str(out / 'tunnel-known-hosts'), '-o', 'ServerAliveInterval=15',
            '-o', 'ServerAliveCountMax=3', '-o', 'ExitOnForwardFailure=yes',
            '-R', '80:127.0.0.1:8766', 'nokey@localhost.run'], stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    try:
        receiver.wait()
    finally:
        tunnel.terminate()
        tunnel.wait(timeout=10)
