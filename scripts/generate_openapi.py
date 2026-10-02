"""Generate the versioned contract; checked-in JSON must match this generator."""
import json
import re
import tempfile
from pathlib import Path
from elmetron.api.app import create_app, VERSION

ROOT=Path(__file__).resolve().parents[1]


def ref(name): return {'$ref':'#/components/schemas/'+name}
def array(schema): return {'type':'array','items':schema}
def obj(properties,required=()): return {'type':'object','properties':properties,'required':list(required)}
def parameter(name,kind='string',**options):
    return {'name':name,'in':'query','required':False,'schema':{'type':kind,**options}}


def contract():
    string={'type':'string'};number={'type':['number','null']};integer={'type':'integer'}
    cursor={'type':['integer','null']}
    schemas={
        'Error':obj({'error':string},('error',)),
        'Status':obj({'state':{'type':'string','enum':['starting','running','reconnecting','stale','stopped','error']},
                     'mode':{'type':'string','enum':['live','demo','archive']},'frames':integer,
                     'detail':{'type':['string','null']},'current_session_id':cursor,
                     'latest_measurement':{'type':['object','null']},'updated_at':{'type':'number'}},('state','mode','frames')),
        'Instrument':obj({'id':integer,'serial':{'type':['string','null']},'model':{'type':['string','null']},'description':{'type':['string','null']}}),
        'Session':obj({'id':integer,'started_at':string,'ended_at':{'type':['string','null']},'note':{'type':['string','null']},
                       'operator_name':{'type':['string','null']},'instrument':ref('Instrument'),
                       'counts':obj({'measurements':integer,'ph_measurements':integer,'redox_measurements':integer,'conductivity_measurements':integer,'markers':integer}),
                       'metadata':{'type':'object'},'latest_measurement_at':{'type':['string','null']},'dominant_parameter':string},('id','started_at','counts')),
        'Measurement':obj({'measurement_id':integer,'frame_id':integer,'session_id':integer,'captured_at':string,'timestamp':string,
                           'device_timestamp':{'type':['string','null']},'device_timezone':{'const':'unknown'},'parameter':string,
                           'value':number,'unit':{'type':['string','null']},'normalized_value':number,'normalized_unit':{'type':['string','null']},
                           'temperature':number,'temperature_unit':{'type':['string','null']},'frame_hex':string,
                           'quality':array(string),'payload':{'type':'object'},'analytics':{'type':'object'},'offset_seconds':number},
                           ('measurement_id','captured_at','value','unit','normalized_value','normalized_unit','device_timezone')),
        'Statistic':obj({'samples':integer,'min':number,'max':number,'average':number,'unit':{'type':['string','null']}},('samples','min','max','average','unit')),
        'Statistics':obj({'by_unit':{'type':'object','additionalProperties':ref('Statistic')},'temperature':ref('Statistic')},('by_unit','temperature')),
        'SessionPage':obj({'sessions':array(ref('Session')),'next_cursor':cursor},('sessions','next_cursor')),
        'MeasurementPage':obj({'measurements':array(ref('Measurement')),'next_cursor':cursor,'limit':integer},('measurements','next_cursor','limit')),
        'Event':obj({'id':integer,'session_id':cursor,'category':string,'label':string,'author':string,'note':string,'offset_seconds':number,'payload':{'type':'object'},'created_at':string}),
        'Evaluation':obj({'session':ref('Session'),'anchor':string,'anchor_timestamp':{'type':['string','null']},'series':array(ref('Measurement')),
                          'markers':array({'type':'object'}),'statistics':ref('Statistics'),'samples':integer,'displayed_samples':integer,
                          'downsampled':{'type':'boolean'},'duration_seconds':number},('series','samples','downsampled','displayed_samples')),
    }
    response_schemas={'health':ref('Status'),'live_status':ref('Status'),'sessions':ref('SessionPage'), 'session':ref('Session'),
        'measurements':ref('MeasurementPage'),'statistics':ref('Statistics'),'evaluation':ref('Evaluation'),
        'instruments':obj({'instruments':array(ref('Instrument'))}), 'markers':obj({'markers':array(ref('Event'))}),
        'calibrations':obj({'calibrations':array(ref('Event'))}), 'logs':obj({'events':array(ref('Event'))}),
        'operators':obj({'operators':array(string)}),'start_capture':ref('Status'),'stop_capture':ref('Status'),'select_archive':ref('Status')}
    bodies={
        'start_capture':obj({'demo':{'type':'boolean','default':False},'name':{'type':'string','maxLength':50},'operator':{'type':'string','maxLength':100}}),
        'new_session':obj({'name':{'type':'string','minLength':1,'maxLength':50}},('name',)),
        'rename':obj({'name':{'type':'string','minLength':1,'maxLength':50}},('name',)),
        'operator':obj({'operator_name':{'type':['string','null'],'maxLength':100}}),
        'default_operator':obj({'operator_name':{'type':'string','maxLength':100}},('operator_name',)),
        'select_archive':obj({'mode':{'type':'string','enum':['demo','archive']}},('mode',)),
        'add_marker':obj({'event_timestamp':string,'offset_seconds':{'type':'number'},'label':string,'author':string,'note':string}),
        'add_calibration':obj({'label':{'type':'string','minLength':1,'maxLength':100},'author':{'type':'string','minLength':1,'maxLength':100},
                               'note':{'type':'string','maxLength':1000},'performed_at':string,'offset_seconds':{'type':'number'}},('label','author')),
    }
    bodies['update_marker']=bodies['add_marker']
    pagination=[parameter('limit','integer',minimum=1,maximum=1000),parameter('cursor','integer',minimum=0)]
    ranges=[parameter('start'),parameter('end'),parameter('parameter',enum=['ph','redox','conductivity'])]
    queries={'sessions':pagination+[parameter('operator'),parameter('start_date'),parameter('end_date'),
             *[parameter('has_'+q,'boolean') for q in ('ph','redox','conductivity')],
             parameter('sort_by',enum=['id','started_at','operator_name','duration','measurement_count']),parameter('order',enum=['asc','desc'])],
             'measurements':pagination+ranges,'statistics':ranges,
             'evaluation':[parameter('anchor',enum=['start','first_marker','last_marker','calibration']),parameter('limit','integer',minimum=2,maximum=10000)],
             'recent':[parameter('minutes','integer',minimum=1,maximum=120)],
             'export':[parameter('format',enum=['csv','json','xml','pdf','zip'])],
             'logs':[parameter('limit','integer',minimum=1,maximum=1000),parameter('since_id','integer'),parameter('level'),parameter('category')]}
    paths={}
    with tempfile.TemporaryDirectory() as home:
        app=create_app(Path(home))
        for rule in app.url_map.iter_rules():
            if not (rule.rule.startswith('/api/v1/') or rule.rule.startswith('/health')): continue
            path=re.sub(r'<(?:int:)?(\w+)>',r'{\1}',rule.rule)
            for method in sorted(rule.methods-{'HEAD','OPTIONS'}):
                endpoint=rule.endpoint
                status='202' if endpoint in ('start_capture','new_session') else '201' if endpoint in ('add_marker','add_calibration') else '200'
                response={'description':'Success','content':{'application/json':{'schema':response_schemas.get(endpoint,{'type':'object'})}}}
                if endpoint=='export':
                    response['content']={t:{'schema':{'type':'string','format':'binary'}} for t in ('text/csv','application/json','application/xml','application/pdf','application/zip')}
                    response['headers']={'X-Content-SHA256':{'description':'SHA256 of downloaded bytes','schema':string}}
                elif endpoint=='bundle': response['content']={'application/zip':{'schema':{'type':'string','format':'binary'}}}
                elif endpoint=='stream': response['content']={'text/event-stream':{'schema':string}}
                elif endpoint=='log_ndjson': response['content']={'application/x-ndjson':{'schema':string}}
                operation={'operationId':endpoint,'summary':endpoint.replace('_',' ').capitalize(), 'responses':{status:response,
                    **{code:{'description':desc,'content':{'application/json':{'schema':ref('Error')}}} for code,desc in
                       [('400','Invalid input'),('403','Host, origin or authorization rejected'),('404','Not found'),('409','Operation conflicts with capture state'),('503','Storage or driver unavailable')]}}}
                params=[{'name':name,'in':'path','required':True,'schema':integer} for name in sorted(rule.arguments)]
                if method=='GET': params+=queries.get(endpoint,[])
                if params: operation['parameters']=params
                if method!='GET':
                    operation['security']=[{'localToken':[]},{'browserCsrf':[]}]
                    if endpoint in bodies: operation['requestBody']={'required':True,'content':{'application/json':{'schema':bodies[endpoint]}}}
                paths.setdefault(path,{})[method.lower()]=operation
    return {'openapi':'3.1.0','info':{'title':'Elmetron local API','version':VERSION,
        'description':'Loopback-only. Original and normalized data. Session cursors are offsets; measurement cursors are IDs. Follow next_cursor until null. MCP uses the same read contracts.',
        'license':{'name':'GPL-3.0-only','identifier':'GPL-3.0-only'}},'servers':[{'url':'http://127.0.0.1:8050'}],
        'paths':paths,'components':{'schemas':schemas,'securitySchemes':{
            'localToken':{'type':'http','scheme':'bearer','description':'Generated config/api-token in the selected data home'},
            'browserCsrf':{'type':'apiKey','in':'header','name':'X-Elmetron-CSRF','description':'Must match the same-origin elmetron_csrf cookie'}}}}


if __name__=='__main__':
    (ROOT/'openapi.json').write_text(json.dumps(contract(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
