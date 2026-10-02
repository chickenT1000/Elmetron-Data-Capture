"""Source developer example: explicit CX-505 USB capture, no remote commands."""
from elmetron.config import DeviceConfig
from elmetron.hardware.device_manager import create_interface
from elmetron.protocols.cx505 import decode_frame


def main():
    interface = create_interface(DeviceConfig())
    try:
        interface.open()
        interface.run_window(10, lambda raw: print(decode_frame(raw)))
    finally:
        interface.close()


if __name__ == '__main__':
    main()
