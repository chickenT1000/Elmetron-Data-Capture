"""Separate installed resources from per-user writable application data."""
from pathlib import Path
import os
import shutil
import sys
from .config import load_config

RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
if not (RESOURCE_ROOT/'config/app.toml').exists():
    RESOURCE_ROOT = Path(sys.prefix)/'share/elmetron'

def data_home(override=None):
    return Path(override or os.environ.get('ELMETRON_DATA_DIR') or (Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'Elmetron')).resolve()

def prepare(home):
    home = Path(home)
    for folder in ('config', 'captures', 'data', 'exports'):
        (home/folder).mkdir(parents=True, exist_ok=True)
    for name in ('app.toml', 'protocols.toml'):
        if not (home/'config'/name).exists():
            shutil.copy2(RESOURCE_ROOT/'config'/name, home/'config'/name)
    if not (home/'config/templates').exists():
        shutil.copytree(RESOURCE_ROOT/'config/templates', home/'config/templates')
    return configuration(home)

def configuration(home):
    home = Path(home)
    cfg = load_config(home/'config/app.toml') if (home/'config/app.toml').exists() else load_config(RESOURCE_ROOT/'config/app.toml')
    for owner, attr in ((cfg.storage,'database_path'), (cfg.export,'export_directory'), (cfg.export,'pdf_template'), (cfg.export,'lims_template')):
        value = getattr(owner, attr)
        if value and not Path(value).is_absolute():
            setattr(owner, attr, home/Path(value))
    return cfg

def read_status(home):
    import json
    try:
        return json.loads((Path(home)/'captures/status.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'state':'stopped', 'mode':'archive', 'frames':0}

def active_home(home):
    return Path(home)/'demo' if read_status(home).get('mode') == 'demo' else Path(home)
