"""Local production HTTP API and same-origin browser application."""
from __future__ import annotations
import io
import json
import math
import os
import secrets
import tempfile
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from ..data import DataRepository, utc, quantity
from ..paths import prepare, configuration, active_home, RESOURCE_ROOT
from ..runtime import CaptureController
from ..storage.database import Database, AuditEvent

VERSION = '1.0.0-beta.1'


def create_app(home):
    home = Path(home)
    cfg = prepare(home)
    database = Database(cfg.storage); database.initialise(); database.close()
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=1024*1024, HOME=home)
    controller = CaptureController(home)
    app.extensions['controller'] = controller
    token_file = home/'config/api-token'
    if not token_file.exists():
        token_file.write_text(secrets.token_urlsafe(32), encoding='utf-8')
    token = token_file.read_text(encoding='utf-8').strip()
    csrf = secrets.token_urlsafe(32)
    import threading
    config_lock = threading.Lock()
    def repository():
        return DataRepository(configuration(active_home(home)).storage.database_path)
    def db():
        return Database(configuration(active_home(home)).storage)
    def payload():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object')
        return data
    def text(value, label='text', maximum=1000, empty=True):
        if not isinstance(value,str) or len(value.strip())>maximum or (not empty and not value.strip()):
            raise ValueError(f'{label} must be a string of 1-{maximum} characters')
        return value.strip()
    def integer(key, default):
        return int(request.args.get(key, default))
    @app.before_request
    def protect():
        if request.host.split(':')[0] not in ('localhost','127.0.0.1','[::1]'):
            return jsonify(error='Invalid local host'),403
        if request.method not in ('GET','HEAD','OPTIONS'):
            bearer = request.headers.get('Authorization','')
            authorized = secrets.compare_digest(bearer, 'Bearer '+token)
            if not authorized:
                origin = request.headers.get('Origin')
                if origin and origin != request.host_url.rstrip('/'):
                    return jsonify(error='Cross-origin operation rejected'),403
                if not (secrets.compare_digest(request.headers.get('X-Elmetron-CSRF',''),csrf) and
                        secrets.compare_digest(request.cookies.get('elmetron_csrf',''),csrf)):
                    return jsonify(error='Local API token or browser CSRF token required'),403
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Cache-Control']='no-store'
        response.set_cookie('elmetron_csrf',csrf,samesite='Strict')
        if request.path.startswith('/api') or request.path.startswith('/health'):
            return response
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
        return response
    from werkzeug.exceptions import HTTPException
    @app.errorhandler(HTTPException)
    def http_error(exc):
        return jsonify(error=exc.description),exc.code
    @app.errorhandler(ValueError)
    @app.errorhandler(TypeError)
    def invalid(exc):
        return jsonify(error=str(exc)),400
    @app.errorhandler(LookupError)
    def missing(exc):
        return jsonify(error=str(exc)),404
    @app.errorhandler(RuntimeError)
    def conflict(exc):
        return jsonify(error=str(exc)),409

    def route(path, **kwargs):
        def decorate(function):
            app.add_url_rule('/api/v1'+path,function.__name__,function,**kwargs)
            app.add_url_rule('/api'+path,function.__name__+'_legacy',function,**kwargs)
            return function
        return decorate

    @app.get('/health')
    def health():
        status = controller.status()
        return jsonify({**status,'version':VERSION,'service':'elmetron','data_home':str(home.resolve()),'last_window_started':None,
                        'log_rotation':{'status':'disabled'},'watchdog_history':[]})
    @route('/live/status')
    def live_status():
        return jsonify(controller.status())
    @route('/capabilities')
    def capabilities():
        return jsonify(version=VERSION, model='CX-505', api_version='v1', mcp_transport='stdio',
                       agent_access='read-only', supported_exports=['csv','json','xml','pdf','zip'])
    @route('/instruments')
    def instruments():
        return jsonify(instruments=repository().instruments())
    @route('/sessions')
    def sessions():
        page = repository().sessions(limit=integer('limit',100),cursor=integer('cursor',0),**{k:v for k,v in request.args.items() if k not in ('limit','cursor')})
        return jsonify(page)
    @route('/sessions/<int:session_id>')
    def session(session_id):
        return jsonify(repository().session(session_id))
    @route('/sessions/<int:session_id>/measurements')
    def measurements(session_id):
        return jsonify(repository().measurements(session_id, cursor=integer('cursor',0),limit=integer('limit',1000),
                        start=request.args.get('start'),end=request.args.get('end'),parameter=request.args.get('parameter')))
    @route('/sessions/<int:session_id>/statistics')
    def statistics(session_id):
        return jsonify(repository().statistics(session_id,start=request.args.get('start'),end=request.args.get('end'),parameter=request.args.get('parameter')))
    @route('/sessions/<int:session_id>/evaluation')
    def evaluation(session_id):
        return jsonify(repository().evaluation(session_id,request.args.get('anchor','start'),integer('limit',10000)))
    @route('/measurements/recent')
    def recent():
        repo = repository()
        sid = controller.status().get('current_session_id')
        if not sid:
            return jsonify(measurements=[],session_id=None)
        start = (datetime.now(timezone.utc)-timedelta(minutes=max(1,min(integer('minutes',10),120)))).isoformat()
        rows=[]
        for r in repo.iter_measurements(sid,start=start):
            rows.append({'timestamp':r['captured_at'],'temperature':r['temperature'],
                         'ph':r['normalized_value'] if r['parameter']=='ph' else None,
                         'redox':r['normalized_value'] if r['parameter']=='redox' else None,
                         'conductivity':r['normalized_value'] if r['parameter']=='conductivity' else None,
                         'quality':r['quality']})
        return jsonify(measurements=rows,session_id=sid)
    @route('/capture/start',methods=['POST'])
    def start_capture():
        data=payload()
        demo=data.get('demo',False)
        if not isinstance(demo,bool):
            raise ValueError('demo must be boolean')
        return jsonify(controller.start(demo,text(data.get('name',''),maximum=50),text(data.get('operator',controller.default_operator),maximum=100))),202
    @route('/capture/stop',methods=['POST'])
    def stop_capture():
        return jsonify(controller.stop())
    @route('/sessions',methods=['POST'])
    def new_session():
        data=payload()
        name=text(data.get('name'),'name',50,False)
        with repository().connection() as conn:
            if any((row[0] or '').casefold()==name.casefold() for row in conn.execute('SELECT note FROM sessions')):
                raise ValueError('A session with this name already exists')
        return jsonify(controller.rotate(name)),202
    @route('/sessions/<int:session_id>/rename',methods=['PATCH'])
    def rename(session_id):
        repository().session(session_id);data=payload();name=text(data.get('name'),'name',50,False)
        database=db()
        try:
            conn=database.connect()
            if conn.execute('SELECT 1 FROM sessions WHERE lower(note)=lower(?) AND id!=?',(name,session_id)).fetchone():
                raise ValueError('A session with this name already exists')
            with conn:
                conn.execute('UPDATE sessions SET note=? WHERE id=?',(name,session_id))
            database.append_audit_event(session_id,AuditEvent('info','metadata','Session renamed',{'name':name}),source='api')
        finally:
            database.close()
        return jsonify(id=session_id,name=name)
    @route('/sessions/<int:session_id>/operator',methods=['PATCH'])
    def operator(session_id):
        repository().session(session_id);data=payload();name=text(data.get('operator_name') or '',maximum=100)
        database=db()
        try:
            with database.connect() as conn:
                conn.execute('UPDATE sessions SET operator_name=? WHERE id=?',(name or None,session_id))
            database.append_audit_event(session_id,AuditEvent('info','metadata','Operator updated',{'operator_name':name}),source='api')
        finally:
            database.close()
        return jsonify(id=session_id,operator_name=name)
    @route('/sessions/active/operator',methods=['PATCH'])
    def active_operator():
        sid=controller.status().get('current_session_id')
        if sid is None:
            raise ValueError('No active session')
        return operator(sid)
    @route('/operators')
    def operators():
        with repository().connection() as conn:
            names=[r[0] for r in conn.execute("SELECT DISTINCT operator_name FROM sessions WHERE operator_name IS NOT NULL AND operator_name != '' ORDER BY operator_name")] if conn else []
        return jsonify(operators=sorted(set(names+[controller.default_operator])-{''}))
    @route('/config/default-operator',methods=['PATCH'])
    def default_operator():
        import tomlkit
        name=text(payload().get('operator_name'),'operator_name',100)
        with config_lock:
            path=home/'config/app.toml';document=tomlkit.parse(path.read_text(encoding='utf-8'))
            document.setdefault('acquisition',{})['default_operator']=name
            temp=path.with_suffix('.tmp');temp.write_text(tomlkit.dumps(document),encoding='utf-8');os.replace(temp,path)
            controller.default_operator=name
        return jsonify(operator_name=name)
    @route('/sessions/<int:session_id>',methods=['DELETE'])
    def delete(session_id):
        repository().session(session_id)
        if controller.status().get('current_session_id')==session_id and controller.status().get('state') in ('running','starting','reconnecting','stale'):
            raise RuntimeError('Stop capture before deleting the active session')
        database=db()
        try:
            conn=database.connect()
            with conn:
                for table in ('annotations','derived_metrics'):
                    conn.execute(f'DELETE FROM {table} WHERE measurement_id IN (SELECT id FROM measurements WHERE session_id=?)',(session_id,))
                for table in ('measurements','raw_frames','audit_events','session_metadata','sessions'):
                    conn.execute(f'DELETE FROM {table} WHERE {"id" if table=="sessions" else "session_id"}=?',(session_id,))
            database.append_system_audit_event(AuditEvent('info','delete','Session deleted',{'session_id':session_id}),source='api')
        finally:
            database.close()
        return jsonify(deleted=True,id=session_id)
    @route('/sessions/<int:session_id>/markers')
    def markers(session_id):
        return jsonify(markers=repository().markers(session_id))
    @route('/sessions/<int:session_id>/calibrations')
    def calibrations(session_id):
        return jsonify(calibrations=repository().markers(session_id,'calibration'))
    def add_event(session_id,category):
        repository().session(session_id);data=payload()
        offset=float(data.get('offset_seconds',0))
        if not math.isfinite(offset):
            raise ValueError('Offset must be finite')
        event={'offset_seconds':offset,'label':text(data.get('label',''),maximum=100,empty=category!='calibration'),
               'note':text(data.get('note','')),'author':text(data.get('author',''),maximum=100,empty=category!='calibration')}
        event['event_timestamp'] = utc(data.get('event_timestamp') or datetime.now(timezone.utc).isoformat())
        if category=='calibration':
            event['performed_at']=utc(data.get('performed_at') or datetime.now(timezone.utc).isoformat())
        database=db()
        try:
            record=database.append_audit_event(session_id,AuditEvent('info',category,event['label'] or category,event),source='api')
        finally:
            database.close()
        return jsonify(id=record,session_id=session_id,**event),201
    @route('/sessions/<int:session_id>/markers',methods=['POST'])
    def add_marker(session_id):
        return add_event(session_id,'marker')
    @route('/sessions/<int:session_id>/calibrations',methods=['POST'])
    def add_calibration(session_id):
        return add_event(session_id,'calibration')
    @route('/sessions/<int:session_id>/markers/<int:marker_id>',methods=['DELETE'])
    def delete_marker(session_id,marker_id):
        database=db()
        try:
            with database.connect() as conn:
                cursor=conn.execute("DELETE FROM audit_events WHERE id=? AND session_id=? AND category='marker'",(marker_id,session_id))
                if not cursor.rowcount:
                    raise LookupError('Marker not found in this session')
            database.append_audit_event(session_id,AuditEvent('info','metadata','Marker removed',{'marker_id':marker_id}),source='api')
        finally:
            database.close()
        return jsonify(deleted=True)
    @route('/sessions/<int:session_id>/markers/<int:marker_id>',methods=['PATCH'])
    def update_marker(session_id,marker_id):
        data=payload()
        offset=float(data.get('offset_seconds',0))
        if not math.isfinite(offset):
            raise ValueError('Offset must be finite')
        database=db()
        try:
            with database.connect() as conn:
                row=conn.execute("SELECT payload_json FROM audit_events WHERE id=? AND session_id=? AND category='marker'",(marker_id,session_id)).fetchone()
                if not row:
                    raise LookupError('Marker not found in this session')
                event=json.loads(row[0] or '{}')
                event.update(offset_seconds=offset, event_timestamp=utc(data.get('event_timestamp')),
                             note=text(data.get('note','')))
                conn.execute('UPDATE audit_events SET payload_json=? WHERE id=?',(json.dumps(event,ensure_ascii=False),marker_id))
        finally:
            database.close()
        return jsonify(id=marker_id,session_id=session_id,**event)
    @route('/sessions/<int:session_id>/export')
    def export(session_id):
        from ..reporting.release import export_snapshot,record_export
        repository().session(session_id)
        fmt=request.args.get('format','csv').lower()
        if fmt not in ('csv','json','xml','pdf','zip'):
            raise ValueError('Supported formats: csv, json, xml, pdf, zip')
        target=active_home(home);cfg=configuration(target)
        folder=tempfile.TemporaryDirectory(dir=target/'exports')
        try:
            path=Path(folder.name)/f'session_{session_id}.{fmt}'
            export_snapshot(cfg.storage.database_path,session_id,path,fmt,cfg.export.pdf_template,cfg.export.lims_template)
            entry=record_export(target,session_id,fmt,path)
            response=send_file(path,as_attachment=True,download_name=path.name,
                             mimetype={'csv':'text/csv','json':'application/json','xml':'application/xml','pdf':'application/pdf','zip':'application/zip'}[fmt])
            response.direct_passthrough=False
            response.call_on_close(folder.cleanup)
        except BaseException:
            folder.cleanup()
            raise
        response.headers['X-Content-SHA256']=entry['sha256']
        return response
    @route('/exports/history')
    def export_history():
        path=active_home(home)/'exports/history.jsonl'
        return jsonify(exports=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()][-100:][::-1] if path.exists() else [])
    @app.get('/health/logs')
    def logs():
        return jsonify(events=repository().events(limit=integer('limit',100),since_id=request.args.get('since_id'),level=request.args.get('level'),category=request.args.get('category')))
    @app.get('/health/logs.ndjson')
    def log_ndjson():
        return Response('\n'.join(json.dumps(e) for e in repository().events()),mimetype='application/x-ndjson')
    @app.get('/health/logs/stream')
    def stream():
        from flask import stream_with_context
        @stream_with_context
        def events():
            last=0
            while True:
                for event in reversed(repository().events()):
                    if event['id']>last:
                        yield 'data: '+json.dumps(event)+'\n\n';last=event['id']
                yield ': heartbeat\n\n';time.sleep(2)
        return Response(events(),mimetype='text/event-stream')
    @app.get('/health/bundle')
    def bundle():
        output=io.BytesIO()
        manifest={'tool':'Elmetron','version':VERSION,'includes_database':False}
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',json.dumps(manifest))
            archive.writestr('status.json',json.dumps(controller.status()))
            archive.writestr('events.json',json.dumps(repository().events()))
        output.seek(0)
        return send_file(output,as_attachment=True,download_name='elmetron-diagnostics.zip',mimetype='application/zip')
    @route('/archive/select',methods=['POST'])
    def select_archive():
        from ..runtime import publish_status
        if controller.status().get('state') in ('starting','running','reconnecting','stale'):
            raise RuntimeError('Stop capture before switching archives')
        mode=payload().get('mode')
        if mode not in ('archive','demo'):
            raise ValueError('mode must be archive or demo')
        if mode=='demo':
            demo_cfg=prepare(home/'demo')
            demo_db=Database(demo_cfg.storage);demo_db.initialise();demo_db.close()
        publish_status(home,{'mode':mode,'state':'stopped','frames':0,'updated_at':time.time()})
        return jsonify(controller.status())
    @route('/server/shutdown',methods=['POST'])
    def shutdown_server():
        controller.stop()
        callback=app.extensions.get('shutdown')
        if callback:
            import threading
            threading.Timer(.5,callback).start()
        return jsonify(stopped=True)
    @route('/stats')
    def counts():
        with repository().connection() as conn:
            return jsonify({t:conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('sessions','measurements','instruments')}) if conn else jsonify(sessions=0,measurements=0,instruments=0)
    @app.get('/openapi.json')
    def openapi():
        return send_file(RESOURCE_ROOT/'openapi.json',mimetype='application/json')
    @app.get('/')
    @app.get('/<path:path>')
    def frontend(path=''):
        root=RESOURCE_ROOT/'ui/dist'
        if not root.exists():
            return jsonify(error='Browser assets missing; build ui with npm run build'),503
        candidate=(root/path).resolve()
        if path and candidate.is_relative_to(root.resolve()) and candidate.is_file():
            return send_from_directory(root,path)
        return send_from_directory(root,'index.html')
    return app
