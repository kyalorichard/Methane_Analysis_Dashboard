"""Single-instance local project storage: SQLite metadata + filesystem Parquet."""
from __future__ import annotations
import hashlib, json, os, shutil, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from analysis_engine.io import dataframe_to_parquet_bytes
from platform_core.data_governance import inspect_dataset

ROOT = Path(os.getenv('LOCAL_PROJECT_STORAGE_DIR', 'data/local_workspace')).expanduser().resolve()
def _db_path():
    # One optional SQLite metadata file can hold workspace, settings, experiments
    # and run-history tables. Legacy LOCAL_WORKSPACE_DB remains an explicit override.
    return Path(os.getenv('METHANE_METADATA_DB') or os.getenv('LOCAL_WORKSPACE_DB') or 'data/methane_metadata.sqlite3').expanduser().resolve()

DB = _db_path()

def _connect():
    ROOT.mkdir(parents=True, exist_ok=True)
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(db_path, timeout=30)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript('''
    CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, owner TEXT NOT NULL, name TEXT NOT NULL, species TEXT NOT NULL, description TEXT, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, name TEXT NOT NULL, species TEXT NOT NULL, storage_path TEXT NOT NULL, file_format TEXT NOT NULL, source_format TEXT, sha256 TEXT, row_count INTEGER, protocol_json TEXT, qc_summary TEXT, created_at TEXT NOT NULL, FOREIGN KEY(project_id) REFERENCES projects(id));
    CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, version_number INTEGER NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(tenant_id,project_id,version_number));
    ''')
    from platform_core.metadata_migrations import migrate_legacy_metadata
    migrate_legacy_metadata(db_path)
    return con

def _now(): return datetime.now(timezone.utc).isoformat()
def _project_dir(tid,pid): return ROOT/'projects'/str(tid)/str(pid)
def _project(con,tid,pid,subject):
    row=con.execute('SELECT * FROM projects WHERE tenant_id=? AND id=? AND owner=?',(tid,pid,subject)).fetchone()
    if row is None: raise PermissionError('Project is not available in this local workspace.')
    return dict(row)
def list_projects(tenant_id,subject):
    with _connect() as c: return [dict(r) for r in c.execute('SELECT id,name,species,description,created_at FROM projects WHERE tenant_id=? AND owner=? ORDER BY created_at DESC',(tenant_id,subject))]
def create_project(tenant_id,subject,name,species,description=''):
    pid=str(uuid.uuid4()); d=_project_dir(tenant_id,pid)
    with _connect() as c:
        c.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?)',(pid,tenant_id,subject,name,species,description,_now()))
    for sub in ('datasets','protocols','configurations','experiments','outputs','versions'): (d/sub).mkdir(parents=True,exist_ok=True)
    return pid
def save_dataset(tenant_id,subject,project_id,filename,raw_bytes,df,species,protocol=None):
    inspect_dataset(df,species); payload=dataframe_to_parquet_bytes(df,compression='snappy'); digest=hashlib.sha256(payload).hexdigest(); did=str(uuid.uuid4())
    with _connect() as c:
        _project(c,tenant_id,project_id,subject)
        target=_project_dir(tenant_id,project_id)/'datasets'/f'{did}.parquet'; target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_suffix('.parquet.tmp'); tmp.write_bytes(payload); os.replace(tmp,target)
        c.execute('INSERT INTO datasets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(did,tenant_id,project_id,filename,species,str(target),'parquet',Path(filename).suffix.lower().lstrip('.'),digest,len(df),json.dumps(protocol or {}),json.dumps(inspect_dataset(df,species),default=str),_now()))
    return {'id':did,'sha256':digest,'source_format':Path(filename).suffix.lower().lstrip('.'),'storage_format':'parquet'}
def list_datasets(tenant_id,project_id,subject):
    with _connect() as c:
        _project(c,tenant_id,project_id,subject)
        rows=c.execute('SELECT id,name,species,file_format,row_count,created_at,sha256,source_format,protocol_json,qc_summary FROM datasets WHERE tenant_id=? AND project_id=? ORDER BY created_at DESC',(tenant_id,project_id)).fetchall()
    out=[]
    for r in rows:
        x=dict(r); x['protocol_json']=json.loads(x['protocol_json'] or '{}'); x['qc_summary']=json.loads(x['qc_summary'] or '{}'); out.append(x)
    return out
def load_dataset(tenant_id,project_id,dataset_id,subject):
    with _connect() as c:
        _project(c,tenant_id,project_id,subject)
        r=c.execute('SELECT * FROM datasets WHERE tenant_id=? AND project_id=? AND id=?',(tenant_id,project_id,dataset_id)).fetchone()
    if r is None: raise PermissionError('Dataset is not available in this project.')
    p=Path(r['storage_path']); raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=r['sha256']: raise IOError('Stored dataset checksum validation failed.')
    return pd.read_parquet(p,engine='pyarrow'),r['name'],r['species']
def get_project(tenant_id,project_id,subject):
    with _connect() as c: return _project(c,tenant_id,project_id,subject)
def duplicate_project(tenant_id,subject,source_project_id,new_name):
    src=get_project(tenant_id,source_project_id,subject); new=create_project(tenant_id,subject,new_name,src['species'],f"Copy of {src['name']}. {src.get('description') or ''}".strip())
    try:
        for d in list_datasets(tenant_id,source_project_id,subject):
            df,fn,sp=load_dataset(tenant_id,source_project_id,d['id'],subject); save_dataset(tenant_id,subject,new,fn,dataframe_to_parquet_bytes(df),df,sp,d.get('protocol_json') or {})
    except Exception as e: raise RuntimeError(f'Project copy {new} is incomplete: {e}') from e
    return new
def create_project_version(tenant_id,subject,project_id,note=''):
    p=get_project(tenant_id,project_id,subject); ds=list_datasets(tenant_id,project_id,subject)
    with _connect() as c:
        v=int(c.execute('SELECT COALESCE(MAX(version_number),0)+1 FROM versions WHERE tenant_id=? AND project_id=?',(tenant_id,project_id)).fetchone()[0])
        snap={'project':p,'datasets':ds,'note':note,'snapshot_type':'metadata_and_dataset_manifest'}
        c.execute('INSERT INTO versions(tenant_id,project_id,version_number,snapshot_json,created_at) VALUES(?,?,?,?,?)',(tenant_id,project_id,v,json.dumps(snap,default=str),_now()))
        (_project_dir(tenant_id,project_id)/'versions'/f'v{v:04d}.json').write_text(json.dumps(snap,indent=2,default=str))
    return v
def list_project_versions(tenant_id,subject,project_id):
    with _connect() as c:
        _project(c,tenant_id,project_id,subject)
        return [{'version_number':r['version_number'],'snapshot_json':json.loads(r['snapshot_json']),'created_at':r['created_at']} for r in c.execute('SELECT * FROM versions WHERE tenant_id=? AND project_id=? ORDER BY version_number DESC',(tenant_id,project_id))]


def save_dataset_configuration(tenant_id, subject, project_id, dataset_id, species, variable_mapping, measurement_protocol):
    """Persist species, variable-role mapping and protocol against one project dataset."""
    payload = {
        'configuration_version': 1,
        'species': species,
        'variable_mapping': variable_mapping or {},
        'measurement_protocol': measurement_protocol or {},
        'updated_at': _now(),
    }
    with _connect() as c:
        _project(c, tenant_id, project_id, subject)
        row = c.execute('SELECT protocol_json FROM datasets WHERE tenant_id=? AND project_id=? AND id=?',
                        (tenant_id, project_id, dataset_id)).fetchone()
        if row is None:
            raise PermissionError('Dataset is not available in this project.')
        existing = json.loads(row['protocol_json'] or '{}')
        existing.update(payload)
        c.execute('UPDATE datasets SET species=?, protocol_json=? WHERE tenant_id=? AND project_id=? AND id=?',
                  (species, json.dumps(existing), tenant_id, project_id, dataset_id))
    return payload


def get_dataset_configuration(tenant_id, subject, project_id, dataset_id):
    with _connect() as c:
        _project(c, tenant_id, project_id, subject)
        row = c.execute('SELECT species, protocol_json FROM datasets WHERE tenant_id=? AND project_id=? AND id=?',
                        (tenant_id, project_id, dataset_id)).fetchone()
    if row is None:
        raise PermissionError('Dataset is not available in this project.')
    stored = json.loads(row['protocol_json'] or '{}')
    # Backward compatibility: pre-configuration releases stored protocol fields at the top level.
    return {
        'species': stored.get('species') or row['species'],
        'variable_mapping': stored.get('variable_mapping') or {},
        'measurement_protocol': stored.get('measurement_protocol') or {
            k: v for k, v in stored.items() if k not in {'configuration_version', 'updated_at', 'species', 'variable_mapping'}
        },
        'configuration_version': stored.get('configuration_version', 0),
        'updated_at': stored.get('updated_at'),
    }
