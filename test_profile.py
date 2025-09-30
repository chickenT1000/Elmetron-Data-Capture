from pathlib import Path
from elmetron import load_config
from elmetron.protocols import load_registry

config = load_config(Path('config/app.toml'))
registry = load_registry(Path('config/protocols.toml'))

print('=== Device Config ===')
print(f'Profile: {config.device.profile}')
print(f'Use profile defaults: {config.device.use_profile_defaults}')
print(f'Poll hex from config: {config.device.poll_hex}')
print(f'Poll interval: {config.device.poll_interval_s}')

print('\n=== Registry Profile ===')
profile = registry.get_profile(config.device.profile or 'cx505')
print(f'Profile name: {profile.name}')
print(f'Poll hex from profile: {profile.poll_hex}')
print(f'Poll interval from profile: {profile.poll_interval_s}')

final_device = registry.apply_to_device(config.device)
print(f'\n=== Final Device (after profile) ===')
print(f'Poll hex: {final_device.poll_hex}')
print(f'Poll interval: {final_device.poll_interval_s}')
