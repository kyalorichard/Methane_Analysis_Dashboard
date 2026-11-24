import os, uuid
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app=FastAPI(title='ICARDA Methane Phenotype Platform API',version='0.3.0')
DATABASE_URL=os.getenv('DATABASE_URL','')
TOKEN=os.getenv('INTERNAL_API_TOKEN','')
engine=create_engine(DATABASE_URL,pool_pre_ping=True) if DATABASE_URL else None

class ProjectCreate(BaseModel):
 name:str=Field(min_length=2,max_length=160)
 species:str=Field(pattern='^(sheep|goat|cattle|buffalo|camel|other)$')
 description:str|None=None

class AnalysisRequest(BaseModel):
 project_id:str
 dataset_id:str|None=None
 module_key:str=Field(min_length=2,max_length=80)
 parameters:dict={}

def service_auth(x_internal_token:str|None=Header(default=None)):
 if not TOKEN or x_internal_token!=TOKEN: raise HTTPException(status_code=401,detail='Unauthorised service request')

def identity(x_auth_request_user:str|None=Header(default=None),x_auth_request_email:str|None=Header(default=None),x_platform_tenant:str|None=Header(default=None)):
    if not all([x_auth_request_user,x_auth_request_email]):
        raise HTTPException(status_code=401,detail='Trusted Microsoft Entra identity headers missing')
    if engine is None: raise HTTPException(503,'DATABASE_URL is not configured')
    with engine.begin() as conn:
        rows=conn.execute(text("""SELECT u.id::text AS user_id,t.id::text AS tenant_id,tm.role FROM users u JOIN tenant_memberships tm ON tm.user_id=u.id JOIN tenants t ON t.id=tm.tenant_id WHERE u.oidc_subject=:sub ORDER BY t.name"""),{'sub':x_auth_request_user}).mappings().all()
    if not rows: raise HTTPException(403,'User is not provisioned in an approved tenant')
    selected=next((r for r in rows if x_platform_tenant and r['tenant_id']==x_platform_tenant),rows[0])
    return {'sub':x_auth_request_user,'email':x_auth_request_email,'user_id':selected['user_id'],'tenant_id':selected['tenant_id'],'role':selected['role']}

@app.get('/health')
def health(): return {'status':'ok','service':'methane-platform-api','database_configured':bool(engine)}

@app.get('/v1/me')
def me(user=Depends(identity)): return user

@app.get('/v1/projects')
def list_projects(user=Depends(identity)):
 if engine is None: raise HTTPException(503,'DATABASE_URL is not configured')
 with engine.begin() as conn:
  conn.execute(text("SELECT set_config('app.tenant_id', :tid, true)"),{'tid':user['tenant_id']})
  rows=conn.execute(text('''SELECT p.id,p.name,p.species,p.description,p.created_at FROM projects p WHERE p.tenant_id=:tid AND (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=p.tenant_id AND tm.user_id=:uid AND tm.role='tenant_admin') OR EXISTS (SELECT 1 FROM project_memberships pm WHERE pm.tenant_id=p.tenant_id AND pm.project_id=p.id AND pm.user_id=:uid)) ORDER BY p.created_at DESC'''),{'tid':user['tenant_id'],'uid':user['user_id']}).mappings().all()
 return [dict(x) for x in rows]

@app.post('/v1/projects')
def create_project(payload:ProjectCreate,user=Depends(identity)):
 if user['role'] not in {'tenant_admin','analyst'}: raise HTTPException(403,'Insufficient role')
 if engine is None: raise HTTPException(503,'DATABASE_URL is not configured')
 project_id=str(uuid.uuid4())
 with engine.begin() as conn:
  conn.execute(text("SELECT set_config('app.tenant_id', :tid, true)"),{'tid':user['tenant_id']})
  conn.execute(text('INSERT INTO projects(id,tenant_id,name,species,description,created_by) VALUES (:id,:tid,:name,:species,:description,:uid)'),{'id':project_id,'tid':user['tenant_id'],'name':payload.name,'species':payload.species,'description':payload.description,'uid':user['user_id']})
  conn.execute(text("INSERT INTO project_memberships(tenant_id,project_id,user_id,role) VALUES (:tid,:pid,:uid,'project_admin')"),{'tid':user['tenant_id'],'pid':project_id,'uid':user['user_id']})
  conn.execute(text("INSERT INTO audit_events(tenant_id,action,resource_type,resource_id,details) VALUES (:tid,'project.created','project',:id,CAST(:details AS jsonb))"),{'tid':user['tenant_id'],'id':project_id,'details':'{}'})
 return {'id':project_id,'name':payload.name,'species':payload.species}

@app.post('/v1/analysis-runs',dependencies=[Depends(service_auth)])
def create_analysis_run(payload:AnalysisRequest):
 # This endpoint is intentionally service-token protected. A production UI/API gateway
 # must also authorize tenant membership and project/dataset ownership before enqueueing.
 return {'status':'integration_pending','module_key':payload.module_key,'message':'Connect tenant-scoped persistence and Celery dispatch before production use.'}
