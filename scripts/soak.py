"""Elapsed-time simulator soak. Success is written only after requested real duration."""
import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from elmetron.paths import prepare
from elmetron.runtime import CaptureController
import psutil


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--hours',type=float,default=24)
    parser.add_argument('--data-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.hours<=0: parser.error('hours must be positive')
    prepare(args.data_dir)
    controller=CaptureController(args.data_dir)
    started=time.time();samples=[];complete=False
    controller.start(demo=True,name='Elapsed-time simulator soak')
    try:
        while time.time()-started<args.hours*3600:
            status=controller.status()
            if controller.process and controller.process.poll() is None:
                process=psutil.Process(controller.process.pid)
                processes=[process]+process.children(recursive=True)
                status['resources']={'rss_bytes':sum(p.memory_info().rss for p in processes),
                                     'cpu_user_seconds':sum(p.cpu_times().user for p in processes),
                                     'cpu_system_seconds':sum(p.cpu_times().system for p in processes),
                                     'process_count':len(processes)}
            samples.append(status)
            progress={'started_at':started,'elapsed_seconds':time.time()-started,'requested_hours':args.hours,'last_status':status,'completed_duration':False}
            (args.data_dir/'soak-progress.json').write_text(json.dumps(progress),encoding='utf-8')
            if status.get('state') in ('error','stale'):
                raise RuntimeError(str(status))
            time.sleep(min(30,max(.1,args.hours*3600-(time.time()-started))))
        complete=True
    finally:
        controller.stop()
        cfg=prepare(args.data_dir/'demo')
        conn=sqlite3.connect(cfg.storage.database_path)
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        fk=conn.execute('PRAGMA foreign_key_check').fetchall()
        conn.close()
        result={'started_at':datetime.fromtimestamp(started,timezone.utc).isoformat(),
                'elapsed_seconds':time.time()-started,'requested_hours':args.hours,'completed_duration':complete,
                'integrity':integrity,'foreign_key_errors':fk,'status_samples':samples,
                'final_status':controller.status()}
        (args.data_dir/'soak-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not complete or integrity!='ok' or fk: raise SystemExit(1)


if __name__=='__main__': main()
