"""Compatibility entry point; production runtime is elmetron.cli.app."""
from elmetron.cli.app import main
if __name__ == '__main__':
    raise SystemExit(main(['serve']))
