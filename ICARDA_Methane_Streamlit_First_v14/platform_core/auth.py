import os
from dataclasses import dataclass
import streamlit as st
from sqlalchemy import create_engine, text
from functools import lru_cache

@dataclass(frozen=True)
class Principal:
    subject: str
    email: str
    name: str
    role: str
    tenant_id: str
    auth_source: str

@lru_cache(maxsize=1)
def _get_auth_engine(url):
    return create_engine(url,pool_pre_ping=True)

def _resolve_memberships(subject: str):
    url=os.getenv("DATABASE_URL", "")
    if not url:
        raise PermissionError("The identity was authenticated, but DATABASE_URL is not configured to resolve tenant membership.")
    engine=_get_auth_engine(url)
    with engine.begin() as conn:
        rows=conn.execute(text("""SELECT t.id::text AS tenant_id, t.name AS tenant_name, tm.role FROM users u JOIN tenant_memberships tm ON tm.user_id=u.id JOIN tenants t ON t.id=tm.tenant_id WHERE u.oidc_subject=:subject ORDER BY t.name"""), {"subject":subject}).mappings().all()
    if not rows:
        raise PermissionError("Your Entra identity is not provisioned in an approved platform tenant.")
    return [dict(r) for r in rows]

def tenant_memberships_for_subject(subject: str):
    return _resolve_memberships(subject)

def current_principal() -> Principal:
    mode=os.getenv("AUTH_MODE", "development").lower()
    if mode == "development":
        return Principal(os.getenv("DEV_USER_SUB","local-developer"),os.getenv("DEV_USER_EMAIL","developer@localhost"),os.getenv("DEV_USER_NAME","Local Developer"),os.getenv("DEV_USER_ROLE","tenant_admin"),os.getenv("DEV_TENANT_ID","local-tenant"),"explicit local development mode")
    if mode != "entra_proxy":
        raise RuntimeError("Unsupported AUTH_MODE. Use entra_proxy in deployed environments.")
    headers=st.context.headers
    email=headers.get(os.getenv("TRUSTED_EMAIL_HEADER","X-Auth-Request-Email"))
    subject=headers.get(os.getenv("TRUSTED_USER_HEADER","X-Auth-Request-User"))
    name=headers.get(os.getenv("TRUSTED_NAME_HEADER","X-Auth-Request-Preferred-Username")) or email
    if not email or not subject:
        raise PermissionError("Trusted Microsoft Entra identity headers are missing.")
    memberships=_resolve_memberships(subject)
    ids=[m["tenant_id"] for m in memberships]
    selected=st.session_state.get("active_tenant_id")
    if selected not in ids: selected=ids[0]
    membership=next(m for m in memberships if m["tenant_id"]==selected)
    return Principal(subject,email,name or email,membership["role"],membership["tenant_id"],"Microsoft Entra ID")

def require_principal():
    try: p=current_principal()
    except Exception as exc:
        st.error(f"Authentication / authorization required: {exc}")
        st.stop()
    st.session_state["principal"]={"subject":p.subject,"email":p.email,"name":p.name,"role":p.role,"tenant_id":p.tenant_id,"auth_source":p.auth_source}
    return p

def require_role(*roles):
    p=require_principal()
    if p.role not in roles:
        st.error("Your account does not have permission to perform this action.")
        st.stop()
    return p
