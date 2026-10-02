"""Installed CLI: production server, local MCP, exports and diagnostics."""
from __future__ import annotations
import argparse
import json
import logging
import signal
import sys
from pathlib import Path
from ..paths import data_home,prepare,configuration,RESOURCE_ROOT


def main(argv=None):
    parser=argparse.ArgumentParser(description='Elmetron CX-505 capture and archives')
    parser.add_argument('--data-dir',help='Writable application directory (default LOCALAPPDATA/Elmetron)')
    sub=parser.add_subparsers(dest='command')
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8050);serve.add_argument('--open-browser',action='store_true')
    sub.add_parser('mcp')
    worker=sub.add_parser('capture-worker');worker.add_argument('--demo',action='store_true');worker.add_argument('--name');worker.add_argument('--operator')
    validate=sub.add_parser('validate-config');validate.add_argument('--config',type=Path);validate.add_argument('--protocols',type=Path);validate.add_argument('--show-effective',action='store_true')
    sub.add_parser('list-devices')
    export=sub.add_parser('export');export.add_argument('--session',required=True,type=int);export.add_argument('--format',choices=['csv','json','xml','pdf','zip'],default='csv');export.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    home=data_home(args.data_dir)
    logging.basicConfig(stream=sys.stderr,level=logging.INFO,format='%(levelname)s %(message)s')
    try:
        if args.command=='mcp':
            from ..mcp_server import create_server
            create_server(home).run(transport='stdio');return 0
        if args.command=='capture-worker':
            from ..runtime import capture_worker
            capture_worker(home,args.demo,args.name,args.operator);return 0
        if args.command=='list-devices':
            from ..hardware.device_manager import list_devices
            from dataclasses import asdict
            print(json.dumps([asdict(d) for d in list_devices()],ensure_ascii=False));return 0
        if args.command=='validate-config':
            from ..config import load_config
            from ..protocols.registry import load_registry
            from ..protocols.validator import validate_registry_file
            config_path=args.config or home/'config/app.toml'
            protocols=args.protocols or home/'config/protocols.toml'
            if args.config and not config_path.is_file():
                raise ValueError(f'Configuration file not found: {config_path}')
            if args.protocols and not protocols.is_file():
                raise ValueError(f'Protocols file not found: {protocols}')
            if not config_path.exists():
                config_path=RESOURCE_ROOT/'config/app.toml'
            if not protocols.exists():
                protocols=RESOURCE_ROOT/'config/protocols.toml'
            cfg=load_config(config_path)
            import tomllib
            raw=tomllib.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.suffix=='.toml' else {}
            unknown=set(raw)-set(cfg.to_dict())
            if unknown:
                raise ValueError('Unknown configuration sections: '+', '.join(sorted(unknown)))
            result=validate_registry_file(protocols)
            if result.errors:
                raise ValueError(str(result.issues))
            load_registry(protocols).apply_to_device(cfg.device)
            from ..config import validate_effective_config
            validate_effective_config(cfg)
            if args.show_effective:
                print(json.dumps(cfg.to_dict(),ensure_ascii=False,indent=2,default=str))
            else:
                print('Configuration and profiles valid')
            return 0
        if args.command=='export':
            from ..reporting.release import export_snapshot
            from ..paths import active_home
            import tempfile, shutil
            cfg=configuration(active_home(home))
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/f'session_{args.session}.{args.format}'
                export_snapshot(cfg.storage.database_path,args.session,path,args.format,cfg.export.pdf_template)
                shutil.copyfile(path,args.output)
            print(args.output);return 0
        from ..api.app import create_app
        from ..runtime import InstanceLock, InstallGuard
        from waitress import create_server
        prepare(home)
        with InstanceLock(home/'captures/server.lock'), InstallGuard():
            app=create_app(home)
            server=create_server(app,host='127.0.0.1',port=getattr(args,'port',8050),threads=8)
            controller=app.extensions['controller']
            import threading
            def shutdown(signum,frame):
                def stop():
                    try:
                        controller.stop()
                    finally:
                        server.close()
                threading.Thread(target=stop,daemon=True).start()
            app.extensions['shutdown'] = server.close
            signal.signal(signal.SIGINT,shutdown);signal.signal(signal.SIGTERM,shutdown)
            if getattr(args,'open_browser',False):
                import webbrowser
                webbrowser.open(f'http://127.0.0.1:{args.port}/')
            try:
                server.run()
            finally:
                controller.stop()
        return 0
    except (OSError,ValueError,TypeError,RuntimeError,LookupError) as exc:
        print(str(exc),file=sys.stderr);return 1


if __name__=='__main__':
    raise SystemExit(main())
