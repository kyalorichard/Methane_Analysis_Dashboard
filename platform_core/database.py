import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL=os.getenv('DATABASE_URL','')
_engine=None
_Session=None

def configured(): return bool(DATABASE_URL)

def _session_factory():
 global _engine,_Session
 if not DATABASE_URL: raise RuntimeError('DATABASE_URL is not configured.')
 if _Session is None:
  _engine=create_engine(DATABASE_URL,pool_pre_ping=True,pool_size=5,max_overflow=10)
  _Session=sessionmaker(bind=_engine,expire_on_commit=False)
 return _Session

@contextmanager
def tenant_session(tenant_id:str):
 Session=_session_factory(); session=Session()
 try:
  # SET LOCAL ensures the tenant context is transaction-scoped.
  session.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"),{'tenant_id':tenant_id})
  yield session
  session.commit()
 except Exception:
  session.rollback();raise
 finally: session.close()
