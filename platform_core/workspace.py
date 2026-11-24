import json
import os
import uuid
from datetime import datetime, timezone
import boto3
import pandas as pd
from sqlalchemy import text
from platform_core.database import tenant_session
from platform_core.data_governance import inspect_dataset
from analysis_engine.io import dataframe_to_parquet_bytes


def _user_id(session, subject: str):
    row=session.execute(text('SELECT id FROM users WHERE oidc_subject=:sub'),{'sub':subject}).first()
    if not row:
        raise PermissionError('Your account has not been provisioned in the platform user registry.')
    return row[0]


def _assert_project_access(session, tenant_id: str, project_id: str, user_id: str, write: bool=False):
    tenant_role=session.execute(text('SELECT role FROM tenant_memberships WHERE tenant_id=:tid AND user_id=:uid'),{'tid':tenant_id,'uid':user_id}).scalar_one_or_none()
    project_role=session.execute(text('SELECT role FROM project_memberships WHERE tenant_id=:tid AND project_id=:pid AND user_id=:uid'),{'tid':tenant_id,'pid':project_id,'uid':user_id}).scalar_one_or_none()
    allowed_read=tenant_role=='tenant_admin' or project_role is not None
    allowed_write=tenant_role in {'tenant_admin','analyst'} or project_role in {'project_admin','analyst','researcher'}
    if not (allowed_write if write else allowed_read):
        raise PermissionError('You do not have access to this project operation.')


def list_projects(tenant_id: str, subject: str):
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        rows=session.execute(text('''
          SELECT p.id::text,p.name,p.species,p.description,p.created_at
          FROM projects p
          WHERE p.tenant_id=:tid AND (
            EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=p.tenant_id AND tm.user_id=:uid AND tm.role='tenant_admin')
            OR EXISTS (SELECT 1 FROM project_memberships pm WHERE pm.tenant_id=p.tenant_id AND pm.project_id=p.id AND pm.user_id=:uid)
          ) ORDER BY p.created_at DESC
        '''),{'tid':tenant_id,'uid':uid}).mappings().all()
    return [dict(r) for r in rows]


def create_project(tenant_id: str, subject: str, name: str, species: str, description: str=''):
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        role=session.execute(text('SELECT role FROM tenant_memberships WHERE tenant_id=:tid AND user_id=:uid'),{'tid':tenant_id,'uid':uid}).scalar_one_or_none()
        if role not in {'tenant_admin','analyst'}:
            raise PermissionError('Only tenant administrators and analysts can create projects.')
        pid=str(uuid.uuid4())
        session.execute(text('INSERT INTO projects(id,tenant_id,name,species,description,created_by) VALUES (:id,:tid,:name,:species,:desc,:uid)'),{'id':pid,'tid':tenant_id,'name':name,'species':species,'desc':description,'uid':uid})
        session.execute(text("INSERT INTO project_memberships(tenant_id,project_id,user_id,role) VALUES (:tid,:pid,:uid,'project_admin')"),{'tid':tenant_id,'pid':pid,'uid':uid})
        session.execute(text("INSERT INTO audit_events(tenant_id,user_id,action,resource_type,resource_id,details) VALUES (:tid,:uid,'project.created','project',:pid,CAST(:details AS jsonb))"),{'tid':tenant_id,'uid':uid,'pid':pid,'details':json.dumps({'species':species})})
    return pid


def save_dataset(tenant_id: str, subject: str, project_id: str, filename: str, raw_bytes: bytes, df: pd.DataFrame, species: str, protocol: dict | None=None):
    """Persist every uploaded dataset as canonical Snappy-compressed Parquet."""
    bucket=os.getenv('S3_BUCKET')
    if not bucket:
        raise RuntimeError('S3_BUCKET is not configured. Dataset persistence is disabled.')
    import hashlib
    from pathlib import Path
    profile=inspect_dataset(df,species)
    source_digest=hashlib.sha256(raw_bytes).hexdigest()
    source_format=Path(filename).suffix.lower().lstrip('.') or 'unknown'
    parquet_bytes=dataframe_to_parquet_bytes(df,compression='snappy')
    parquet_digest=hashlib.sha256(parquet_bytes).hexdigest()
    dataset_id=str(uuid.uuid4())
    key=f'tenants/{tenant_id}/projects/{project_id}/datasets/{dataset_id}/data.parquet'
    s3=boto3.client('s3',region_name=os.getenv('AWS_REGION'))
    s3.put_object(Bucket=bucket,Key=key,Body=parquet_bytes,ContentType='application/vnd.apache.parquet',ServerSideEncryption='aws:kms',Metadata={'sha256':parquet_digest,'source-sha256':source_digest,'species':species,'dataset-id':dataset_id,'source-format':source_format,'storage-format':'parquet'})
    try:
        with tenant_session(tenant_id) as session:
            uid=_user_id(session,subject)
            _assert_project_access(session,tenant_id,project_id,uid,write=True)
            project=session.execute(text('SELECT id FROM projects WHERE id=:pid AND tenant_id=:tid'),{'pid':project_id,'tid':tenant_id}).first()
            if not project: raise PermissionError('Project is not accessible in the active tenant.')
            session.execute(text("""INSERT INTO datasets(id,tenant_id,project_id,name,species,storage_key,file_format,source_format,sha256,source_sha256,row_count,schema_json,qc_summary,protocol_json,uploaded_by)
              VALUES (:id,:tid,:pid,:name,:species,:key,'parquet',:source_format,:sha,:source_sha, :rows,CAST(:schema AS jsonb),CAST(:qc AS jsonb),CAST(:protocol AS jsonb),:uid)"""),
              {'id':dataset_id,'tid':tenant_id,'pid':project_id,'name':filename,'species':species,'key':key,'source_format':source_format,'sha':parquet_digest,'source_sha':source_digest,'rows':len(df),'schema':json.dumps({c:str(t) for c,t in df.dtypes.items()}),'qc':json.dumps(profile),'protocol':json.dumps(protocol or {}),'uid':uid})
            session.execute(text("INSERT INTO audit_events(tenant_id,user_id,action,resource_type,resource_id,details) VALUES (:tid,:uid,'dataset.uploaded','dataset',:did,CAST(:details AS jsonb))"),{'tid':tenant_id,'uid':uid,'did':dataset_id,'details':json.dumps({'sha256':parquet_digest,'source_sha256':source_digest,'source_format':source_format,'storage_format':'parquet','row_count':len(df),'species':species})})
    except Exception:
        s3.delete_object(Bucket=bucket,Key=key)
        raise
    return {'id':dataset_id,'storage_key':key,'sha256':parquet_digest,'source_sha256':source_digest,'source_format':source_format,'storage_format':'parquet','profile':profile}


def list_datasets(tenant_id: str, project_id: str, subject: str):
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        _assert_project_access(session,tenant_id,project_id,uid,write=False)
        rows=session.execute(text('SELECT id::text,name,species,file_format,row_count,created_at,sha256,source_format,protocol_json,qc_summary,schema_json FROM datasets WHERE tenant_id=:tid AND project_id=:pid ORDER BY created_at DESC'),{'tid':tenant_id,'pid':project_id}).mappings().all()
    return [dict(r) for r in rows]


def load_dataset(tenant_id: str, project_id: str, dataset_id: str, subject: str):
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        _assert_project_access(session,tenant_id,project_id,uid,write=False)
        row=session.execute(text('SELECT storage_key,name,species,file_format FROM datasets WHERE tenant_id=:tid AND project_id=:pid AND id=:did'),{'tid':tenant_id,'pid':project_id,'did':dataset_id}).mappings().first()
    if not row: raise PermissionError('Dataset is not available in this project.')
    s3=boto3.client('s3',region_name=os.getenv('AWS_REGION'))
    obj=s3.get_object(Bucket=os.environ['S3_BUCKET'],Key=row['storage_key'])
    raw=obj['Body'].read()
    ext=row['file_format'].lower()
    from io import BytesIO
    if ext in {'parquet','pq'}: df=pd.read_parquet(BytesIO(raw),engine='pyarrow')
    elif ext in {'xlsx','xls'}: df=pd.read_excel(BytesIO(raw))
    else: df=pd.read_csv(BytesIO(raw))  # backward compatibility for pre-migration datasets
    return df,row['name'],row['species']


def get_project(tenant_id: str, project_id: str, subject: str):
    """Return project metadata after enforcing tenant/project read access."""
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        _assert_project_access(session,tenant_id,project_id,uid,write=False)
        row=session.execute(text("SELECT id::text,name,species,description,created_at FROM projects WHERE tenant_id=:tid AND id=:pid"),{'tid':tenant_id,'pid':project_id}).mappings().first()
    if not row: raise PermissionError('Project is not available in this tenant.')
    return dict(row)

def duplicate_project(tenant_id: str, subject: str, source_project_id: str, new_name: str):
    """Create an independent project copy, including stored datasets and protocol metadata."""
    source=get_project(tenant_id,source_project_id,subject)
    new_id=create_project(tenant_id,subject,new_name,source['species'],f"Copy of {source['name']}. {source.get('description') or ''}".strip())
    try:
        for item in list_datasets(tenant_id,source_project_id,subject):
            df,filename,species=load_dataset(tenant_id,source_project_id,item['id'],subject)
            protocol=item.get('protocol_json') or {}
            # Preserve the scientific table and protocol; storage receives a new immutable object.
            raw=dataframe_to_parquet_bytes(df)
            save_dataset(tenant_id,subject,new_id,filename,raw,df,species,protocol)
    except Exception:
        # Keep a clearly named partial copy rather than deleting data without a separate audit trail.
        raise RuntimeError(f'Project copy {new_id} was created but dataset replication failed. Review the partial project before retrying.')
    return new_id


def create_project_version(tenant_id: str, subject: str, project_id: str, note: str = ""):
    """Record an immutable metadata/dataset-manifest checkpoint for a project."""
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        _assert_project_access(session,tenant_id,project_id,uid,write=True)
        project=session.execute(text("SELECT id::text,name,species,description FROM projects WHERE tenant_id=:tid AND id=:pid"),{'tid':tenant_id,'pid':project_id}).mappings().first()
        if not project: raise PermissionError('Project is not available.')
        datasets=session.execute(text("SELECT id::text,name,species,file_format,row_count,sha256,protocol_json FROM datasets WHERE tenant_id=:tid AND project_id=:pid ORDER BY created_at"),{'tid':tenant_id,'pid':project_id}).mappings().all()
        version=int(session.execute(text("SELECT COALESCE(MAX(version_number),0)+1 FROM project_versions WHERE tenant_id=:tid AND project_id=:pid"),{'tid':tenant_id,'pid':project_id}).scalar_one())
        snapshot={'project':dict(project),'datasets':[dict(x) for x in datasets],'note':note,'snapshot_type':'metadata_and_dataset_manifest'}
        session.execute(text("INSERT INTO project_versions(tenant_id,project_id,version_number,snapshot_json,created_by) VALUES (:tid,:pid,:version,CAST(:snapshot AS jsonb),:uid)"),{'tid':tenant_id,'pid':project_id,'version':version,'snapshot':json.dumps(snapshot,default=str),'uid':uid})
        session.execute(text("INSERT INTO audit_events(tenant_id,user_id,action,resource_type,resource_id,details) VALUES (:tid,:uid,'project.version.created','project',:pid,CAST(:details AS jsonb))"),{'tid':tenant_id,'uid':uid,'pid':project_id,'details':json.dumps({'version':version,'note':note})})
    return version


def list_project_versions(tenant_id: str, subject: str, project_id: str):
    with tenant_session(tenant_id) as session:
        uid=_user_id(session,subject)
        _assert_project_access(session,tenant_id,project_id,uid,write=False)
        rows=session.execute(text("SELECT version_number,snapshot_json,created_at FROM project_versions WHERE tenant_id=:tid AND project_id=:pid ORDER BY version_number DESC"),{'tid':tenant_id,'pid':project_id}).mappings().all()
    return [dict(x) for x in rows]


def save_dataset_configuration(tenant_id: str, subject: str, project_id: str, dataset_id: str,
                               species: str, variable_mapping: dict, measurement_protocol: dict):
    """Persist dataset-scoped species and measurement configuration in protocol_json."""
    payload = {
        'configuration_version': 1,
        'species': species,
        'variable_mapping': variable_mapping or {},
        'measurement_protocol': measurement_protocol or {},
    }
    with tenant_session(tenant_id) as session:
        uid = _user_id(session, subject)
        _assert_project_access(session, tenant_id, project_id, uid, write=True)
        row = session.execute(text('SELECT protocol_json FROM datasets WHERE tenant_id=:tid AND project_id=:pid AND id=:did'),
                              {'tid': tenant_id, 'pid': project_id, 'did': dataset_id}).mappings().first()
        if not row:
            raise PermissionError('Dataset is not available in this project.')
        existing = row.get('protocol_json') or {}
        existing.update(payload)
        session.execute(text('UPDATE datasets SET species=:species, protocol_json=CAST(:protocol AS jsonb) WHERE tenant_id=:tid AND project_id=:pid AND id=:did'),
                        {'species': species, 'protocol': json.dumps(existing), 'tid': tenant_id, 'pid': project_id, 'did': dataset_id})
        session.execute(text("INSERT INTO audit_events(tenant_id,user_id,action,resource_type,resource_id,details) VALUES (:tid,:uid,'dataset.configuration.updated','dataset',:did,CAST(:details AS jsonb))"),
                        {'tid': tenant_id, 'uid': uid, 'did': dataset_id, 'details': json.dumps({'species': species, 'configuration_version': 1})})
    return payload


def get_dataset_configuration(tenant_id: str, subject: str, project_id: str, dataset_id: str):
    with tenant_session(tenant_id) as session:
        uid = _user_id(session, subject)
        _assert_project_access(session, tenant_id, project_id, uid, write=False)
        row = session.execute(text('SELECT species, protocol_json FROM datasets WHERE tenant_id=:tid AND project_id=:pid AND id=:did'),
                              {'tid': tenant_id, 'pid': project_id, 'did': dataset_id}).mappings().first()
    if not row:
        raise PermissionError('Dataset is not available in this project.')
    stored = row.get('protocol_json') or {}
    return {
        'species': stored.get('species') or row['species'],
        'variable_mapping': stored.get('variable_mapping') or {},
        'measurement_protocol': stored.get('measurement_protocol') or {
            k: v for k, v in stored.items() if k not in {'configuration_version', 'species', 'variable_mapping'}
        },
        'configuration_version': stored.get('configuration_version', 0),
    }
