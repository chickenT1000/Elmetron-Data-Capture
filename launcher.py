"""Desktop shortcut entry point. Opens the installed browser app without Node."""
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path
from elmetron.paths import data_home,prepare
from elmetron.runtime import command_prefix


def launch(home=None,port=8050,open_browser=True):
    home=data_home(home)
    url=f'http://127.0.0.1:{port}'
    def healthy():
        import json
        try:
            with urllib.request.urlopen(url+'/health',timeout=1) as response:
                status = json.loads(response.read())
                if status.get('service') == 'elmetron' and status.get('data_home') != str(home):
                    raise RuntimeError('Another Elmetron data directory is using this port.')
                return status.get('service') == 'elmetron'
        except (OSError,ValueError):
            return False
    if not healthy():
        prepare(home)
        log=(home/'captures/server.log').open('a',encoding='utf-8')
        process=subprocess.Popen([*command_prefix(),'--data-dir',str(home),'serve','--port',str(port)],
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        log.close()
        for _ in range(100):
            if healthy():
                break
            if process.poll() is not None:
                raise RuntimeError(f'Backend could not start. See {home}/captures/server.log; port {port} may be occupied.')
            time.sleep(.1)
        else:
            raise RuntimeError('Backend startup timed out; inspect server.log')
    if open_browser:
        webbrowser.open(url+'/')


if __name__=='__main__':
    try:
        import argparse
        parser=argparse.ArgumentParser()
        parser.add_argument('--data-dir');parser.add_argument('--port',type=int,default=8050)
        parser.add_argument('--no-browser',action='store_true')
        args=parser.parse_args()
        launch(args.data_dir,args.port,not args.no_browser)
    except Exception as exc:
        import tkinter.messagebox
        tkinter.messagebox.showerror('Elmetron',str(exc))
