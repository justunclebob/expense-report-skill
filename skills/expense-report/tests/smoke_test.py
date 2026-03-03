#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'scripts'/'ledger.py'
DELIVER=ROOT/'scripts'/'deliver_report.py'

def run(*args):
    p=subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

with tempfile.TemporaryDirectory() as td:
    base=Path(td)/'expense'
    rc,out,err=run('python3',str(LEDGER),'init','--root',str(base))
    assert rc==0, err

    rc,out,err=run('python3',str(LEDGER),'add','--root',str(base),'--text','咖啡 .5')
    assert rc==0, err
    obj=json.loads(out)
    assert abs(obj['entry']['amount']-0.5)<1e-9

    rc,out,err=run('python3',str(LEDGER),'add','--root',str(base),'--text','今天心情很好')
    assert rc!=0 and '未识别到金额' in (out+err)

    rc,out,err=run('python3',str(LEDGER),'add','--root',str(base),'--text','退款 -20')
    assert rc==0
    obj=json.loads(out)
    assert obj['entry']['category']=='退款与冲减'

    rc,out,err=run('python3',str(LEDGER),'confirm-category','--root',str(base),'--category','乱写分类')
    assert rc!=0

    run('python3',str(LEDGER),'rates','--root',str(base))
    rc,out,err=run('python3',str(LEDGER),'report','--root',str(base),'--period','monthly','--date','2026-03-03')
    assert rc==0, err

    rc,out,err=run('python3',str(DELIVER),'--root',str(base),'--period','monthly','--format','html','--dry-run')
    assert rc==0 and 'validated report file only' in out

print('smoke_test: OK')
