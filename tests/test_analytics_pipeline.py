from __future__ import annotations

import json
from datetime import datetime
from typing import Iterator

import pytest

import cx505_d2xx

from elmetron.analytics.engine import AnalyticsEngine
from elmetron.config import AppConfig, AnalyticsConfig, StorageConfig
from elmetron.ingestion.pipeline import FrameIngestor
from elmetron.reporting.exporters import (
    CsvExportOptions,
    export_csv,
    export_session_csv,
    export_session_json,
    export_session_lims_xml,
    export_session_pdf,
)
from elmetron.reporting.session import load_session_summary
from elmetron.storage.database import Database, DeviceMetadata


def test_analytics_engine_computes_metrics() -> None:
    config = AnalyticsConfig(
        enabled=True,
        moving_average_window=3,
        stability_window=3,
        temperature_coefficient=0.05,
        reference_temperature=25.0,
        max_history=10,
    )
    engine = AnalyticsEngine(config)

    template = {
        'measurement': {
            'unit': 'pH',
            'temperature': 24.5,
        }
    }

    results = []
    for value in [7.00, 7.05, 7.10]:
        payload = {
            'measurement': {
                **template['measurement'],
                'value': value,
            }
        }
        results.append(engine.process(payload))

    first_metrics = results[0]
    assert first_metrics is not None
    assert first_metrics['samples_tracked'] == 1
    assert 'moving_average' not in first_metrics

    second_metrics = results[1]
    assert second_metrics is not None
    assert second_metrics['samples_tracked'] == 2

    final_metrics = results[2]
    assert final_metrics is not None
    assert pytest.approx(final_metrics['moving_average'], rel=1e-3) == 7.05
    assert 'stability_index' in final_metrics
    compensation = final_metrics.get('temperature_compensation')
    assert compensation is not None
    assert compensation['method'] == 'ph_slope'


@pytest.fixture()
def seeded_session(tmp_path, monkeypatch) -> Iterator[tuple[Database, int]]:
    storage_cfg = StorageConfig(
        database_path=tmp_path / 'elmetron.sqlite',
        ensure_directories=True,
    )
    database = Database(storage_cfg)
    database.initialise()
    session = database.start_session(
        datetime.utcnow(),
        DeviceMetadata(serial='SN123', description='Test Device', model='CX-505'),
    )

    app_config = AppConfig()
    app_config.analytics.enabled = True
    app_config.analytics.moving_average_window = 2
    app_config.analytics.stability_window = 2
    app_config.analytics.max_history = 8
    app_config.analytics.temperature_coefficient = 0.02

    engine = AnalyticsEngine(app_config.analytics)
    ingestor = FrameIngestor(app_config.ingestion, session, analytics=engine)

    values = iter([7.00, 7.05, 7.08])

    def fake_decode(_frame: bytes):
        value = next(values, 7.10)
        return {
            'measurement': {
                'value': value,
                'unit': 'pH',
                'temperature': 24.0,
                'temperature_unit': 'C',
            }
        }

    monkeypatch.setattr(cx505_d2xx, '_decode_frame', fake_decode)
    for _ in range(3):
        assert ingestor.handle_frame(b'\x00') is not None

    session.close()
    try:
        yield database, session.id
    finally:
        database.close()


def test_frame_ingestor_persists_metrics(seeded_session) -> None:
    database, session_id = seeded_session
    conn = database.connect()
    row = conn.execute('SELECT metrics_json FROM derived_metrics LIMIT 1').fetchone()
    assert row is not None
    metrics = json.loads(row['metrics_json'])
    assert 'temperature_compensation' in metrics
    assert metrics.get('unit') == 'pH'


def test_exporters_include_analytics(seeded_session, tmp_path) -> None:
    database, session_id = seeded_session
    csv_path = tmp_path / 'session.csv'
    json_path = tmp_path / 'session.json'
    xml_path = tmp_path / 'session.xml'

    export_session_csv(database.path, session_id, csv_path)
    export_session_json(database.path, session_id, json_path)
    export_session_lims_xml(database.path, session_id, xml_path)

    csv_text = csv_path.read_text(encoding='utf-8')
    assert 'analytics_json' in csv_text

    summary = load_session_summary(database.path, session_id)
    assert summary is not None

    json_payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert isinstance(json_payload, list)
    assert json_payload[0]['analytics']

    xml_text = xml_path.read_text(encoding='utf-8')
    assert '<Analytics>' in xml_text


def test_export_session_pdf_generates_pdf(seeded_session, tmp_path) -> None:
    database, session_id = seeded_session
    pdf_path = tmp_path / 'session.pdf'

    export_session_pdf(database.path, session_id, pdf_path)

    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes.startswith(b'%PDF')
    assert b'Elmetron Session Report' in pdf_bytes


def test_export_csv_handles_empty_iterable(tmp_path) -> None:
    csv_path = tmp_path / 'empty.csv'

    export_csv([], csv_path)

    assert csv_path.read_text(encoding='utf-8') == ''

def test_export_session_csv_compact_mode(seeded_session, tmp_path) -> None:
    database, session_id = seeded_session
    csv_path = tmp_path / 'session_compact.csv'

    options = CsvExportOptions(compact=True)
    export_session_csv(database.path, session_id, csv_path, options=options)

    lines = csv_path.read_text(encoding='utf-8').splitlines()
    assert lines, 'CSV output should contain at least the header row'
    header = lines[0]
    assert 'payload_json' not in header
    assert 'analytics_moving_average' in header


def test_export_session_pdf_template(tmp_path, seeded_session) -> None:
    database, session_id = seeded_session
    template_path = tmp_path / 'report.tmpl'
    template_path.write_text(
        "Session \nFirst value \n",
        encoding='utf-8',
    )
    pdf_path = tmp_path / 'session_template.pdf'

    export_session_pdf(
        database.path,
        session_id,
        pdf_path,
        template=template_path,
        recent_limit=3,
    )

    pdf_bytes = pdf_path.read_bytes()
    assert b'Session' in pdf_bytes
    assert b'First value' in pdf_bytes


def test_export_session_lims_xml_template(seeded_session, tmp_path) -> None:
    database, session_id = seeded_session
    template_path = tmp_path / 'lims.tmpl'
    template_path.write_text(
        """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<SessionReport id=\"\">
  
  <Measurements>
    
  </Measurements>
</SessionReport>
""",
        encoding='utf-8',
    )
    xml_path = tmp_path / 'session_template.xml'

    export_session_lims_xml(
        database.path,
        session_id,
        xml_path,
        template=template_path,
    )

    xml_text = xml_path.read_text(encoding='utf-8')
    assert '<SessionReport' in xml_text
    assert '<Measurements>' in xml_text
