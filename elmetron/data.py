"""Shared, read-only data contracts for HTTP, MCP and charts."""
from __future__ import annotations
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utc(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def quantity(unit):
    key = (unit or '').lower().replace('μ', 'u').replace('µ', 'u').replace(' ', '')
    if key == 'ph':
        return 'ph', 'pH', 1.0
    if key in ('mv', 'orp', 'mvrel'):
        return 'redox', 'mV', 1.0
    if key in ('us/cm', 'ms/cm', 's/cm'):
        return 'conductivity', 'µS/cm', {'us/cm': 1.0, 'ms/cm': 1000.0, 's/cm': 1000000.0}[key]
    return 'unknown', unit, 1.0


def stats(values, unit):
    values = [v for v in values if isinstance(v, (float, int)) and math.isfinite(v)]
    return {'samples': len(values), 'min': min(values) if values else None,
            'max': max(values) if values else None,
            'average': math.fsum(values) / len(values) if values else None, 'unit': unit}


class DataRepository:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        # Never create or migrate a database on a read path (including MCP).
        if not self.path.exists():
            yield None
            return
        conn = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def instruments(self):
        with self.connection() as conn:
            return [dict(r) for r in conn.execute('SELECT id, serial, description, model FROM instruments ORDER BY id')] if conn else []

    def _summary(self, conn, row):
        item = dict(row)
        counts = dict(conn.execute('SELECT COUNT(*) measurements, MAX(f.captured_at) latest FROM measurements m JOIN raw_frames f ON f.id=m.frame_id WHERE m.session_id=?', (row['id'],)).fetchone())
        parameter_counts = {'ph': 0, 'redox': 0, 'conductivity': 0}
        for unit in conn.execute('SELECT unit, COUNT(*) n FROM measurements WHERE session_id=? GROUP BY unit', (row['id'],)):
            q = quantity(unit['unit'])[0]
            if q in parameter_counts:
                parameter_counts[q] += unit['n']
        item.update({'started_at': utc(row['started_at']), 'ended_at': utc(row['ended_at']),
            'instrument': {k: row[k] for k in ('serial', 'model', 'description')},
            'counts': {'measurements': counts['measurements'], **{q + '_measurements': n for q, n in parameter_counts.items()},
                       'markers': conn.execute("SELECT COUNT(*) FROM audit_events WHERE session_id=? AND category='marker'", (row['id'],)).fetchone()[0]},
            'dominant_parameter': max(parameter_counts, key=parameter_counts.get) if any(parameter_counts.values()) else 'none',
            'latest_measurement_at': utc(counts['latest']),
            'metadata': dict(conn.execute('SELECT key,value FROM session_metadata WHERE session_id=?', (row['id'],)).fetchall())})
        return item

    def sessions(self, limit=100, cursor=0, **filters):
        # Session cursors are offsets into the filtered, sorted archive. Measurements use stable IDs.
        limit = max(1, min(int(limit), 1000))
        cursor = max(0, int(cursor))
        clauses, args = [], []
        for key, column, op in [('operator', 's.operator_name', 'LIKE'), ('start_date', 's.started_at', '>='), ('end_date', 's.started_at', '<=')]:
            if filters.get(key):
                clauses.append(f'{column} {op} ?')
                args.append('%' + filters[key] + '%' if op == 'LIKE' else filters[key])
        units = {'ph': ('ph',), 'redox': ('mv','orp','mvrel'), 'conductivity': ('us/cm','ms/cm','s/cm')}
        for q, keys in units.items():
            flag = filters.get('has_' + q)
            if flag is not None:
                if flag not in (True, False, 'true', 'false'):
                    raise ValueError('Parameter filters must be boolean')
                clause = "EXISTS(SELECT 1 FROM measurements m WHERE m.session_id=s.id AND lower(replace(replace(replace(m.unit,'µ','u'),'μ','u'),' ','')) IN (" + ','.join('?' for _ in keys) + '))'
                clauses.append(clause if flag in (True, 'true') else 'NOT ' + clause)
                args.extend(keys)
        order = filters.get('order', 'asc')
        sort = filters.get('sort_by', 'id')
        sorts = {'id': 's.id', 'started_at': 's.started_at', 'operator_name': 's.operator_name',
                 'duration': 'julianday(COALESCE(s.ended_at,s.started_at))-julianday(s.started_at)',
                 'measurement_count': '(SELECT COUNT(*) FROM measurements WHERE session_id=s.id)'}
        if sort not in sorts or order not in ('asc','desc'):
            raise ValueError('Invalid session sort')
        with self.connection() as conn:
            if conn is None:
                return {'sessions': [], 'next_cursor': None}
            query = 'SELECT s.*, i.serial, i.model, i.description FROM sessions s LEFT JOIN instruments i ON i.id=s.instrument_id'
            if clauses:
                query += ' WHERE ' + ' AND '.join(clauses)
            query += f' ORDER BY {sorts[sort]} {order}, s.id {order} LIMIT ? OFFSET ?'
            rows = conn.execute(query, (*args, limit+1, cursor)).fetchall()
            return {'sessions': [self._summary(conn,r) for r in rows[:limit]],
                    'next_cursor': cursor+limit if len(rows)>limit else None}

    def session(self, session_id):
        with self.connection() as conn:
            row = conn.execute('SELECT s.*, i.serial, i.model, i.description FROM sessions s LEFT JOIN instruments i ON i.id=s.instrument_id WHERE s.id=?', (session_id,)).fetchone() if conn else None
            if not row:
                raise LookupError('Session not found')
            return self._summary(conn,row)

    def measurements(self, session_id, cursor=0, limit=1000, start=None, end=None, parameter=None, through=None):
        self.session(session_id)
        limit = max(1, min(int(limit), 1000))
        clauses, args = ['m.session_id=?', 'm.id>?'], [session_id, int(cursor)]
        for bound, op in [(start, '>='), (end, '<=')]:
            if bound:
                clauses.append(f'julianday(f.captured_at) {op} julianday(?)')
                args.append(utc(bound))
        if through is not None:
            clauses.append('m.id<=?'); args.append(through)
        if parameter:
            units = {'ph': ['ph'], 'redox': ['mv', 'orp', 'mvrel'], 'conductivity': ['us/cm', 'ms/cm', 's/cm']}
            if parameter not in units:
                raise ValueError('Unknown parameter')
            keys = units[parameter]
            clauses.append("lower(replace(replace(replace(m.unit,'µ','u'),'μ','u'),' ','')) IN (" + ','.join('?' for _ in keys) + ')')
            args.extend(keys)
        with self.connection() as conn:
            rows = conn.execute('SELECT m.*, f.captured_at, f.frame_hex, d.metrics_json FROM measurements m JOIN raw_frames f ON f.id=m.frame_id LEFT JOIN derived_metrics d ON d.measurement_id=m.id WHERE ' + ' AND '.join(clauses) + ' ORDER BY m.id LIMIT ?', (*args, limit + 1)).fetchall()
        records = []
        for row in rows[:limit]:
            r = dict(row)
            q, unit, factor = quantity(r['unit'])
            r.update({'measurement_id': r['id'], 'timestamp': utc(r['captured_at']),
                      'captured_at': utc(r['captured_at']), 'device_timestamp': r['measurement_timestamp'],
                      'device_timezone': 'unknown', 'parameter': q, 'normalized_unit': unit,
                      'normalized_value': r['value'] * factor if r['value'] is not None else None,
                      'quality': ['unknown_unit'] if q == 'unknown' else [],
                      'payload': json.loads(r.pop('payload_json')), 'analytics': json.loads(r.pop('metrics_json') or '{}')})
            records.append(r)
        return {'measurements': records, 'next_cursor': rows[limit - 1]['id'] if len(rows) > limit else None, 'limit': limit}

    def iter_measurements(self, session_id, **filters):
        with self.connection() as conn:
            through = conn.execute('SELECT COALESCE(MAX(id),0) FROM measurements WHERE session_id=?',(session_id,)).fetchone()[0] if conn else 0
        cursor = 0
        while True:
            page = self.measurements(session_id, cursor=cursor, through=through, **filters)
            yield from page['measurements']
            cursor = page['next_cursor']
            if cursor is None:
                break

    def statistics(self, session_id, **filters):
        groups = {}
        def add(key, value):
            group = groups.setdefault(key, {'samples':0,'min':None,'max':None,'average':None,'unit':key})
            if value is None or not math.isfinite(value):
                return
            group['samples'] += 1
            group['min'] = value if group['min'] is None else min(group['min'],value)
            group['max'] = value if group['max'] is None else max(group['max'],value)
            old = group['average'] or 0
            group['average'] = old + (value-old)/group['samples']
        for r in self.iter_measurements(session_id, **filters):
            add(r['normalized_unit'] or 'unknown', r['normalized_value'])
            add('__temperature', r['temperature'])
        temperature = groups.pop('__temperature',stats([], 'C'))
        temperature['unit'] = 'C'
        return {'by_unit':groups,'temperature':temperature}

    def events(self, session_id=None, category=None, limit=500, since_id=None, level=None):
        clauses, args = [], []
        if session_id is not None:
            self.session(session_id)
            clauses.append('session_id=?'); args.append(session_id)
        if since_id is not None:
            clauses.append('id>?'); args.append(int(since_id))
        if level:
            clauses.append('level=?'); args.append(level)
        if category:
            clauses.append('category=?'); args.append(category)
        with self.connection() as conn:
            if not conn:
                return []
            rows = conn.execute('SELECT * FROM audit_events' + (' WHERE ' + ' AND '.join(clauses) if clauses else '') + ' ORDER BY id DESC' + (' LIMIT ?' if limit is not None else ''), (*args, min(1000, max(1, int(limit)))) if limit is not None else args).fetchall()
        return [{**dict(r), 'payload': json.loads(r['payload_json'] or '{}')} for r in rows]

    def markers(self, session_id, category='marker'):
        return [{**r, **r['payload'], 'created_at': utc(r['created_at']), 'marker_number': i+1, 'event_timestamp': r['payload'].get('event_timestamp') or utc(r['created_at'])} for i,r in enumerate(reversed(self.events(session_id, category, limit=None)))]

    def evaluation(self, session_id, anchor='start', limit=10000):
        session = self.session(session_id)
        markers = sorted(self.markers(session_id), key=lambda m: m.get('offset_seconds', 0))
        start = datetime.fromisoformat(session['started_at'].replace('Z', '+00:00'))
        shift = 0
        if anchor not in ('start','first_marker','last_marker','calibration'):
            raise ValueError('Invalid anchor')
        if anchor == 'calibration':
            markers = sorted(self.markers(session_id,'calibration'), key=lambda m:m.get('offset_seconds',0))
        if markers and anchor in ('first_marker', 'last_marker', 'calibration'):
            shift = float(markers[-1 if anchor == 'last_marker' else 0]['offset_seconds'])
        limit = min(10000,max(2,int(limit)))
        counts = {q:session['counts'].get(q+'_measurements',0) for q in ('ph','redox','conductivity')}
        counts['unknown'] = session['counts']['measurements']-sum(counts.values())
        counts = {q:n for q,n in counts.items() if n}
        if len(counts)*2 > limit:
            raise ValueError('Chart limit must allow at least two points per quantity')
        budget = max(2,limit//max(1,len(counts)))
        sizes = {q:max(1,math.ceil(n/(budget//2))) for q,n in counts.items()}
        buckets={};series=[];groups={};total=0
        def add_stat(unit,value):
            group=groups.setdefault(unit,{'samples':0,'min':None,'max':None,'average':None,'unit':unit})
            if value is None or not math.isfinite(value): return
            group['samples']+=1
            group['min']=value if group['min'] is None else min(group['min'],value)
            group['max']=value if group['max'] is None else max(group['max'],value)
            old=group['average'] or 0
            group['average']=old+(value-old)/group['samples']
        def flush(bucket):
            if bucket['min'] is not None:
                series.extend({r['id']:r for r in (bucket['min'],bucket['max'])}.values())
            elif bucket['first'] is not None:
                series.append(bucket['first'])
        for r in self.iter_measurements(session_id):
            total+=1
            add_stat(r['normalized_unit'] or 'unknown',r['normalized_value'])
            add_stat('__temperature',r['temperature'])
            point={**r,'original_value':r['value'],'original_unit':r['unit'],
                   'value':r['normalized_value'],'unit':r['normalized_unit'],
                   'offset_seconds':(datetime.fromisoformat(r['captured_at'].replace('Z','+00:00'))-start).total_seconds()-shift}
            q=r['parameter']; bucket=buckets.setdefault(q,{'n':0,'first':None,'min':None,'max':None})
            bucket['n']+=1
            bucket['first']=bucket['first'] or point
            if point['value'] is not None:
                if bucket['min'] is None or point['value']<bucket['min']['value']:bucket['min']=point
                if bucket['max'] is None or point['value']>bucket['max']['value']:bucket['max']=point
            if bucket['n']>=sizes.get(q,1):
                flush(bucket);buckets[q]={'n':0,'first':None,'min':None,'max':None}
        for bucket in buckets.values():flush(bucket)
        series.sort(key=lambda r:r['id'])
        temperature=groups.pop('__temperature',stats([],'C'));temperature['unit']='C'
        statistics={'by_unit':groups,'temperature':temperature}
        by_unit = statistics['by_unit']
        value_stats = next(iter(by_unit.values())) if len(by_unit) == 1 else stats([], None)
        from datetime import timedelta
        return {'session': session, 'anchor': anchor, 'anchor_timestamp': utc(start + timedelta(seconds=shift)),
                'series': series, 'markers': [{'marker_number': i+1, 'offset_seconds': m['offset_seconds']-shift,
                                             'offset_minutes': (m['offset_seconds']-shift)/60} for i,m in enumerate(markers)],
                'statistics': {**statistics, 'value': value_stats}, 'samples': total,
                'downsampled': len(series) < total, 'displayed_samples': len(series),
                'duration_seconds': (datetime.fromisoformat(session['ended_at'].replace('Z', '+00:00'))-start).total_seconds() if session['ended_at'] else None}
