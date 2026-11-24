# Production architecture starter

This package extends the Streamlit v2 research prototype with an initial architecture scaffold:
PostgreSQL tenant schema/RLS, FastAPI service boundary, Celery worker entry point, Redis queue,
S3-compatible MinIO service for local integration, and OIDC/reverse-proxy security guidance.

## Start local integration stack
1. Copy `.env.production.example` to `.env` and replace every placeholder with strong secrets.
2. Install production dependencies: `pip install -r requirements-production.txt`.
3. Run `docker compose -f docker-compose.production.yml up --build`.
4. Dashboard: http://localhost:8501; API health: http://localhost:8000/health; MinIO console: http://localhost:9001.

The compose file is a development/integration environment, not a production security baseline.
Do not expose it directly to the public internet. OIDC, tenant membership enforcement,
database transaction scoping, object-store authorization, persistent API workflows and
analysis task implementations must be completed and tested before production deployment.

See `docs/PRODUCTION_ROADMAP.md` and `infra/REVERSE_PROXY_AUTH.md`.
