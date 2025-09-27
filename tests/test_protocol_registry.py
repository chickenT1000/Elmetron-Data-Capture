import pytest

from elmetron.config import DEFAULT_POLL_HEX, DeviceConfig
from elmetron.protocols import DEFAULT_PROFILES, DEFAULT_PROFILE_NAME, ProtocolRegistry


def test_apply_to_device_applies_profile_defaults():
    registry = ProtocolRegistry.from_dict(DEFAULT_PROFILES)
    device = DeviceConfig(profile='cx505', poll_hex=None, poll_interval_s=None)

    profile = registry.apply_to_device(device)

    assert profile.name == 'cx505'
    assert device.profile == 'cx505'
    assert device.transport == 'ftdi'
    assert device.poll_hex == DEFAULT_POLL_HEX
    assert device.poll_interval_s == pytest.approx(1.0)
    assert device.baud == 115200
    assert device.parity == 'E'


def test_apply_to_device_falls_back_to_default_when_missing():
    registry = ProtocolRegistry.from_dict(DEFAULT_PROFILES)
    device = DeviceConfig(profile='unknown-model')

    profile = registry.apply_to_device(device)

    assert profile.name == DEFAULT_PROFILE_NAME
    assert device.profile == DEFAULT_PROFILE_NAME


def test_apply_to_device_respects_no_defaults_for_serial_settings():
    profiles = {
        'custom': {
            'description': 'Custom profile',
            'transport': 'ftdi',
            'baud': 9600,
            'poll_hex': 'AA BB',
            'poll_interval_s': 2.5,
            'latency_timer_ms': 16,
        }
    }
    registry = ProtocolRegistry.from_dict(profiles)
    device = DeviceConfig(
        profile='custom',
        use_profile_defaults=False,
        baud=4800,
        poll_hex=None,
        poll_interval_s=None,
        latency_timer_ms=8,
    )

    profile = registry.apply_to_device(device)

    assert profile.name == 'custom'
    # Serial defaults unchanged.
    assert device.baud == 4800
    assert device.latency_timer_ms == 8
    # Non-serial helpers still populated when explicitly unset.
    assert device.poll_hex == 'AA BB'
    assert device.poll_interval_s == pytest.approx(2.5)


def test_apply_to_device_raises_when_profile_not_found_and_no_default():
    registry = ProtocolRegistry.from_dict({'custom': {'transport': 'ftdi'}})
    device = DeviceConfig(profile='missing')

    with pytest.raises(KeyError):
        registry.apply_to_device(device)

def test_command_definition_includes_retry_metadata():
    registry = ProtocolRegistry.from_dict(DEFAULT_PROFILES)
    profile = registry.get('cx505')
    assert profile is not None
    command = profile.commands['calibrate_ph7']
    assert command.category == 'calibration'
    assert command.default_max_retries == 2
    assert command.default_retry_backoff_s == pytest.approx(1.5)
    assert command.calibration_label == 'ph7_buffer'
