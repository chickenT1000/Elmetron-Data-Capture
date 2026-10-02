"""Smoke the windowless launcher with no Python/Node on its PATH."""
import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--exe', type=Path, required=True)
parser.add_argument('--data-dir', type=Path, required=True)
args = parser.parse_args()
home = args.data_dir.resolve()
if home.exists():
    raise SystemExit('Use a new disposable data directory')
environment = dict(os.environ)
environment['PATH'] = os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'), os.environ['SystemRoot']])
desktop = subprocess.Popen([str(args.exe.resolve()), '--data-dir', str(home), '--port', '18053', '--no-browser'],
                           env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
url = 'http://127.0.0.1:18053'
status = None
try:
    for _ in range(120):
        try:
            with urllib.request.urlopen(url+'/health', timeout=1) as response:
                status = json.load(response)
            break
        except (OSError, ValueError):
            time.sleep(.25)
    assert status and status['data_home'] == str(home), status
    assert status['service'] == 'elmetron'
finally:
    if status and status.get('data_home') == str(home):
        token = (home/'config/api-token').read_text(encoding='utf-8').strip()
        request = urllib.request.Request(url+'/api/v1/server/shutdown', method='POST',
                                         headers={'Authorization': 'Bearer '+token})
        with urllib.request.urlopen(request, timeout=20) as response:
            assert json.load(response)['stopped']
    desktop.wait(timeout=20)
print('Packaged windowless desktop launcher started the correct backend without Python/Node PATH')
