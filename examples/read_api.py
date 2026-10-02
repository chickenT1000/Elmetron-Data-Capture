"""Read the full archive through REST v1 using only Python's standard library."""
import json
from urllib.request import urlopen

BASE = 'http://127.0.0.1:8050/api/v1'


def get(path):
    with urlopen(BASE + path, timeout=30) as response:
        return json.load(response)


def pages(path, key):
    cursor = 0
    while True:
        page = get(f'{path}?limit=1000&cursor={cursor}')
        yield from page[key]
        cursor = page['next_cursor']
        if cursor is None:
            break


if __name__ == '__main__':
    for session in pages('/sessions', 'sessions'):
        for row in pages(f"/sessions/{session['id']}/measurements", 'measurements'):
            print(row['captured_at'], row['value'], row['unit'], row['normalized_value'], row['normalized_unit'])
