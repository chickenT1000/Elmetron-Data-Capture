"""Archive exactly the checked-out Git commit and hash every release download."""
import hashlib
import subprocess
from pathlib import Path

from elmetron.api.app import VERSION

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / 'dist/installers'
output.mkdir(parents=True, exist_ok=True)
source = output / f'Elmetron-{VERSION}-source.zip'
subprocess.run(['git', 'archive', '--format=zip', '--prefix=Elmetron/',
                f'--output={source}', 'HEAD'], cwd=ROOT, check=True)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
(output / 'SOURCE_COMMIT.txt').write_text(commit + '\n', encoding='ascii')
lines = []
for path in sorted(output.iterdir()):
    if path.is_file() and path.name != 'SHA256SUMS.txt':
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        lines.append(f'{digest}  {path.name}\n')
(output / 'SHA256SUMS.txt').write_text(''.join(lines), encoding='ascii')
print(f'Release artifacts prepared for {commit}')
