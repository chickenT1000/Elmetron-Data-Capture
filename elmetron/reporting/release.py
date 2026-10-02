"""Complete, snapshot-consistent exports with original and normalized data."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from ..data import DataRepository
from .exporters import export_session_pdf

_history_lock = threading.Lock()


def file_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def export_snapshot(database_path, session_id, output, fmt, pdf_template=None, lims_template=None):
    """Caller owns an isolated output directory. SQLite backup supplies one stable snapshot."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = output.parent / 'snapshot.sqlite'
    source = sqlite3.connect(Path(database_path).resolve().as_uri() + '?mode=ro', uri=True)
    destination = sqlite3.connect(snapshot)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    repo = DataRepository(snapshot)
    session = repo.session(session_id)
    formats = ('csv', 'json', 'xml', 'pdf') if fmt == 'zip' else (fmt,)
    files = []
    try:
        for kind in formats:
            path = output.parent / f'session_{session_id}.{kind}'
            if kind == 'csv':
                fields = ['measurement_id', 'captured_at', 'device_timestamp', 'device_timezone',
                          'parameter', 'value', 'unit', 'normalized_value', 'normalized_unit',
                          'temperature', 'temperature_unit', 'frame_hex', 'quality', 'payload', 'analytics']
                with path.open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.DictWriter(stream, fields, extrasaction='ignore')
                    writer.writeheader()
                    for row in repo.iter_measurements(session_id):
                        writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
            elif kind == 'json':
                with path.open('w',encoding='utf-8') as stream:
                    stream.write('{"session":' + json.dumps(session,ensure_ascii=False) + ',"measurements":[')
                    for i,row in enumerate(repo.iter_measurements(session_id)):
                        stream.write((',' if i else '') + json.dumps(row,ensure_ascii=False,allow_nan=False))
                    stream.write('],"statistics":' + json.dumps(repo.statistics(session_id),ensure_ascii=False))
                    stream.write(',"markers":' + json.dumps(repo.markers(session_id),ensure_ascii=False))
                    stream.write(',"calibrations":' + json.dumps(repo.markers(session_id,'calibration'),ensure_ascii=False) + '}')
            elif kind == 'xml':
                # Stream one measurement element at a time; ElementTree escapes user-controlled text.
                with path.open('w',encoding='utf-8') as stream:
                    stream.write('<?xml version="1.0" encoding="utf-8"?>\n<SessionReport>')
                    metadata=ET.Element('Session',id=str(session_id))
                    ET.SubElement(metadata,'MetadataJson').text=json.dumps(session,ensure_ascii=False)
                    stream.write(ET.tostring(metadata,encoding='unicode'))
                    stream.write('<Measurements>')
                    for row in repo.iter_measurements(session_id):
                        node=ET.Element('Measurement',id=str(row['measurement_id']))
                        for key,value in row.items():
                            ET.SubElement(node,key).text=json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value) if value is not None else ''
                        stream.write(ET.tostring(node,encoding='unicode'))
                    stream.write('</Measurements>')
                    for category in ('marker','calibration'):
                        node=ET.Element(category+'Records')
                        node.text=json.dumps(repo.markers(session_id,category),ensure_ascii=False)
                        stream.write(ET.tostring(node,encoding='unicode'))
                    stream.write('</SessionReport>')
            elif kind == 'pdf':
                export_session_pdf(snapshot,session_id,path,template=pdf_template)
            else:
                raise ValueError('Supported formats: csv, json, xml, pdf, zip')
            files.append(path)
        if fmt == 'zip':
            manifest={'schema_version':1,'session_id':session_id,'generated_at':datetime.now(timezone.utc).isoformat(),
                      'measurement_count':session['counts']['measurements'],
                      'files':{p.name:{'sha256':file_sha256(p),'bytes':p.stat().st_size} for p in files}}
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in files:
                    archive.write(path,path.name)
                archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        return output
    finally:
        snapshot.unlink(missing_ok=True)


def record_export(home, session_id, fmt, artifact):
    is_path = isinstance(artifact, (str, Path))
    entry={'generated_at':datetime.now(timezone.utc).isoformat(),'session_id':session_id,'format':fmt,
           'sha256':file_sha256(artifact) if is_path else hashlib.sha256(artifact).hexdigest(),
           'bytes':Path(artifact).stat().st_size if is_path else len(artifact)}
    with _history_lock, (Path(home)/'exports/history.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(entry)+'\n'); stream.flush(); os.fsync(stream.fileno())
    return entry
