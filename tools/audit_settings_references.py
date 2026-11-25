#!/usr/bin/env python3
"""Static reference inventory for settings keys across dashboard source.

A source reference is not proof of runtime effect. The report deliberately
separates source references from tested runtime consumption.
"""
from __future__ import annotations
import json
from pathlib import Path
from analysis_engine.settings_config import defaults
ROOT=Path(__file__).resolve().parents[1]
SCAN=[ROOT/'analysis_engine',ROOT/'pages',ROOT/'api',ROOT/'worker']

def flatten(obj,prefix=''):
    out=[]
    for k,v in obj.items():
        if k=='schema_version': continue
        path=f'{prefix}.{k}' if prefix else k
        if isinstance(v,dict): out.extend(flatten(v,path))
        else: out.append(path)
    return out

def main():
    files=[]
    for base in SCAN:
        if base.exists(): files.extend(base.rglob('*.py'))
    contents={str(p.relative_to(ROOT)):p.read_text(encoding='utf-8',errors='ignore') for p in files}
    rows=[]
    for key in flatten(defaults()):
        leaf=key.split('.')[-1]
        hits=[name for name,src in contents.items() if key in src or (f'get(\"{leaf}\")' in src or f"get('{leaf}')" in src)]
        rows.append({'setting':key,'source_references':hits,
                     'static_reference_found':bool(hits),
                     'runtime_effect':'not established by static scan'})
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    (out/'settings_reference_audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(f'{len(rows)} settings inventoried; {sum(r["static_reference_found"] for r in rows)} have source references.')
if __name__=='__main__': main()
