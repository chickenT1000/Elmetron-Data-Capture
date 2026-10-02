import asyncio
import json
from datetime import datetime

import pytest

from elmetron.api.app import create_app
from elmetron.config import StorageConfig
from elmetron.data import DataRepository
from elmetron.paths import prepare
from elmetron.storage.database import Database, DeviceMetadata
from elmetron.storage.session_buffer import SessionBuffer


@pytest.fixture
def archive(tmp_path):
    cfg = prepare(tmp_path)
    db = Database(cfg.storage)
    db.initialise()
    session = db.start_session(datetime(2026, 1, 1), DeviceMetadata('TEST', 'Test', 'CX-505'))
    yield tmp_path, db, session
    db.close()


def decoded(unit='pH', value=7.0, temperature=0):
    return {'measurement': {'value': value, 'value_unit': unit, 'temperature': temperature,
                            'temperature_unit': 'C', 'timestamp': '2026-01-01T12:00:00'}}


def test_short_session_is_preserved(archive):
    home, db, session = archive
    session.store_capture(datetime(2026, 1, 1), b'raw', decoded())
    session.close()
    assert DataRepository(db.path).session(session.id)['counts']['measurements'] == 1


def test_earliest_audit_schema_migrates_without_losing_history(archive):
    from elmetron.storage.database import AuditEvent
    home, db, session = archive
    conn = db.connect()
    with conn:
        conn.execute('DROP TABLE audit_events')
        conn.execute('''CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
            level TEXT NOT NULL, category TEXT NOT NULL, message TEXT NOT NULL,
            payload_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id))''')
        conn.execute("INSERT INTO audit_events(id,session_id,level,category,message,payload_json) VALUES(42,?,'info','capture','Original','{}')", (session.id,))
        conn.execute('PRAGMA user_version=0')
    db.initialise()
    row = conn.execute('SELECT * FROM audit_events WHERE id=42').fetchone()
    assert row['message'] == 'Original' and row['source'] == 'backend'
    db.append_system_audit_event(AuditEvent('info','system','Migrated'))
    assert conn.execute('SELECT COUNT(*) FROM audit_events WHERE session_id IS NULL').fetchone()[0] == 1
    assert db.path.with_name(db.path.name+'.pre-v2.bak').exists()
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    db.initialise()
    assert conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0] == 2


def test_marker_edit_is_atomic_and_keeps_identity(archive):
    home, db, session = archive
    client = create_app(home).test_client()
    headers = {'Authorization':'Bearer '+(home/'config/api-token').read_text()}
    url = f'/api/v1/sessions/{session.id}/markers'
    original = client.post(url, json={'offset_seconds':10,'note':'Original'}, headers=headers).json
    updated = client.patch(f"{url}/{original['id']}",json={'offset_seconds':20,'note':'Changed','event_timestamp':'2026-01-01T00:00:20Z'},headers=headers)
    assert updated.status_code == 200 and updated.json['id'] == original['id']
    failed = client.patch(f"{url}/{original['id']}",json={'offset_seconds':'invalid'},headers=headers)
    assert failed.status_code == 400
    markers = client.get(url).json['markers']
    assert len(markers) == 1 and markers[0]['note'] == 'Changed' and markers[0]['offset_seconds'] == 20


@pytest.mark.parametrize('field,value', [('chunk_size',0), ('baud',-1), ('poll_interval_s',float('nan'))])
def test_invalid_effective_transport_bounds(field,value):
    from elmetron.config import AppConfig, validate_effective_config
    cfg = AppConfig()
    setattr(cfg.device,field,value)
    with pytest.raises(ValueError):
        validate_effective_config(cfg)


def test_journal_replay_is_idempotent_and_preserves_metrics(archive):
    home, db, session = archive
    journal = SessionBuffer(None, session.id, home / 'captures')
    journal.create(datetime(2026, 1, 1), {'serial': 'TEST'})
    journal.append_measurement(datetime(2026, 1, 1), b'raw', decoded(), {'mean': 7})
    journal.close()
    for _ in range(2):
        result = SessionBuffer.recover_orphaned_buffers(home / 'captures', db, delete_after_recovery=False)
        assert result['failed_recoveries'] == 0
    assert db.connect().execute('SELECT COUNT(*) FROM measurements').fetchone()[0] == 1
    assert json.loads(db.connect().execute('SELECT metrics_json FROM derived_metrics').fetchone()[0]) == {'mean': 7}


def test_partial_journal_kept_and_retry_does_not_duplicate(archive):
    home, db, session = archive
    journal = SessionBuffer(None, session.id, home / 'captures')
    journal.create(datetime(2026, 1, 1), {'serial': 'TEST'})
    journal.append_measurement(datetime(2026, 1, 1), b'raw', decoded())
    journal.close()
    with journal.buffer_path.open('a') as out:
        out.write('{"type":')
    for _ in range(2):
        result = SessionBuffer.recover_orphaned_buffers(home / 'captures', db)
        assert result['failed_recoveries'] == 1
        assert journal.buffer_path.exists()
    assert db.connect().execute('SELECT COUNT(*) FROM measurements').fetchone()[0] == 1


def test_missing_session_is_not_resurrected(archive):
    home, db, session = archive
    path = home / 'captures/session_999_buffer.jsonl'
    path.write_text(json.dumps({'type':'session_start','session_id':999,'device':{}}))
    assert SessionBuffer.recover_orphaned_buffers(home/'captures', db)['failed_recoveries'] == 1
    assert db.connect().execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1


def test_units_zero_and_negative_temperature_and_full_pagination(archive):
    home, db, session = archive
    for i in range(1005):
        session.store_capture(datetime(2026, 1, 1), b'raw', decoded('mS/cm', 1.2, -1 if i else 0))
    repo = DataRepository(db.path)
    rows = list(repo.iter_measurements(session.id))
    assert len(rows) == 1005
    assert rows[0]['value'] == 1.2 and rows[0]['unit'] == 'mS/cm'
    assert rows[0]['normalized_value'] == 1200 and rows[0]['normalized_unit'] == 'µS/cm'
    assert rows[0]['temperature'] == 0 and rows[-1]['temperature'] == -1
    assert rows[0]['device_timezone'] == 'unknown'
    assert repo.statistics(session.id)['by_unit']['µS/cm']['samples'] == 1005
    evaluation = repo.evaluation(session.id, limit=10)
    assert evaluation['samples'] == 1005 and evaluation['downsampled']
    assert len(evaluation['series']) <= 10


def test_session_filters_applied_before_pagination(archive):
    home, db, session = archive
    for i in range(5):
        s = db.start_session(datetime(2026,1,1), session.metadata)
        if i % 2:
            s.store_capture(datetime(2026,1,1),b'raw',decoded())
    repo = DataRepository(db.path)
    page = repo.sessions(limit=1, has_ph=True, order='desc')
    assert len(page['sessions']) == 1
    next_page = repo.sessions(limit=1,cursor=page['next_cursor'],has_ph=True,order='desc')
    assert len(next_page['sessions']) == 1
    assert next_page['sessions'][0]['id'] < page['sessions'][0]['id']
    assert next_page['next_cursor'] is None


def test_api_security_and_fk_safe_delete(archive):
    home, db, session = archive
    session.store_capture(datetime(2026,1,1),b'raw',decoded(), {'mean':7})
    app = create_app(home)
    client = app.test_client()
    path = f'/api/v1/sessions/{session.id}'
    assert client.delete(path).status_code == 403
    client.get('/health')
    csrf = client.get_cookie('elmetron_csrf').value
    assert client.delete(path,headers={'X-Elmetron-CSRF':csrf,'Origin':'https://evil.example'}).status_code == 403
    assert client.get('/health',headers={'Host':'evil.example'}).status_code == 403
    assert client.delete(path,headers={'X-Elmetron-CSRF':csrf}).status_code == 200
    assert db.connect().execute('PRAGMA foreign_key_check').fetchall() == []
    assert client.get(path).status_code == 404


def test_calibration_requires_author_and_label(archive):
    home, db, session = archive
    client = create_app(home).test_client()
    token = (home/'config/api-token').read_text()
    headers={'Authorization':'Bearer '+token}
    path=f'/api/v1/sessions/{session.id}/calibrations'
    assert client.post(path,json={},headers=headers).status_code == 400
    assert client.post(path,json={'label':'pH 7','author':'Jan'},headers=headers).status_code == 201
    assert client.get(path).json['calibrations'][0]['author'] == 'Jan'


def test_mcp_is_read_only_and_matches_http(archive):
    from mcp import Client
    from elmetron.mcp_server import create_server
    home, db, session = archive
    session.store_capture(datetime(2026,1,1),b'raw',decoded())
    expected = create_app(home).test_client().get(f'/api/v1/sessions/{session.id}/measurements').json
    async def check():
        async with Client(create_server(home)) as client:
            tools = await client.list_tools()
            assert len(tools.tools) == 8
            assert all(t.annotations.read_only_hint for t in tools.tools)
            result = await client.call_tool('get_measurements',{'session_id':session.id})
            assert not result.is_error
            assert result.structured_content == expected
    asyncio.run(check())


def test_mcp_empty_archive_does_not_create_database(tmp_path):
    from mcp import Client
    from elmetron.mcp_server import create_server
    async def check():
        async with Client(create_server(tmp_path)) as client:
            result = await client.call_tool('list_sessions',{})
            assert not result.is_error
    asyncio.run(check())
    assert not (tmp_path/'data').exists()


def test_migration_backed_up_once_and_future_schema_rejected(archive):
    home, db, session = archive
    with db.connect() as conn:
        conn.execute('PRAGMA user_version=0')
    db.initialise()
    backup = db.path.with_name(db.path.name+'.pre-v2.bak')
    assert backup.exists()
    timestamp = backup.stat().st_mtime_ns
    db.initialise()
    assert backup.stat().st_mtime_ns == timestamp
    with db.connect() as conn:
        conn.execute('PRAGMA user_version=99')
    with pytest.raises(RuntimeError):
        db.initialise()


def test_windows_status_replace_retries_without_interrupting_capture(tmp_path, monkeypatch):
    from elmetron.runtime import publish_status
    from elmetron.paths import read_status
    import os
    real_replace = os.replace
    calls = []
    def transient(source, target):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError('Reader holds Windows file')
        real_replace(source, target)
    monkeypatch.setattr('elmetron.runtime.os.replace', transient)
    monkeypatch.setattr('elmetron.runtime.time.sleep', lambda _: None)
    assert publish_status(tmp_path, {'state':'running','frames':10})
    assert read_status(tmp_path)['frames'] == 10
    assert len(calls) == 3


def test_zip_full_data_and_manifest_hashes(archive, tmp_path):
    import hashlib
    import zipfile
    from elmetron.reporting.release import export_snapshot
    home, db, session = archive
    for _ in range(12):
        session.store_capture(datetime(2026,1,1),b'raw',decoded('mS/cm',1.2,-1))
    output=tmp_path/'zip/session_1.zip'
    export_snapshot(db.path,session.id,output,'zip')
    with zipfile.ZipFile(output) as bundle:
        manifest=json.loads(bundle.read('manifest.json'))
        assert manifest['measurement_count']==12
        for filename,info in manifest['files'].items():
            assert hashlib.sha256(bundle.read(filename)).hexdigest()==info['sha256']
        data=json.loads(bundle.read('session_1.json'))
        assert len(data['measurements'])==12
        assert data['measurements'][0]['normalized_value']==1200


def test_contract_matches_routes_and_measurement_response(archive):
    from scripts.generate_openapi import contract
    import jsonschema
    home, db, session = archive
    session.store_capture(datetime(2026,1,1),b'raw',decoded())
    document=contract()
    checked=json.loads(__import__('pathlib').Path('openapi.json').read_text(encoding='utf-8'))
    assert checked==document
    assert len(document['paths'])>20
    response=create_app(home).test_client().get(f'/api/v1/sessions/{session.id}/measurements').json
    schema={**document,'$ref':'#/components/schemas/MeasurementPage'}
    jsonschema.Draft202012Validator(schema).validate(response)
