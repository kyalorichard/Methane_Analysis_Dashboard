"""Render the ECS task definition template using deployment environment variables."""
import json
import os
import re
import sys
from pathlib import Path

TEMPLATE=Path(__file__).resolve().parents[1]/'ecs-task-definition.template.json'
REQUIRED=['AWS_ACCOUNT_ID','AWS_REGION','IMAGE_TAG','ECS_EXECUTION_ROLE_ARN','APP_TASK_ROLE_ARN','DATABASE_URL_SECRET_ARN','S3_BUCKET','INTERNAL_API_TOKEN_SECRET_ARN','ENTRA_TENANT_ID','ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET_ARN','OAUTH_COOKIE_SECRET_ARN','APP_DOMAIN','ALLOWED_EMAIL_DOMAIN']
missing=[k for k in REQUIRED if not os.getenv(k)]
if missing:
    raise SystemExit('Missing required environment variables: '+', '.join(missing))
raw=TEMPLATE.read_text(encoding='utf-8')
def repl(match):
    key=match.group(1)
    if key not in os.environ:
        raise SystemExit(f'Missing environment variable: {key}')
    return os.environ[key]
rendered=re.sub(r'\$\{([A-Z0-9_]+)\}',repl,raw)
data=json.loads(rendered)
Path(sys.argv[1] if len(sys.argv)>1 else 'ecs-task-definition.rendered.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('Rendered ECS task definition. Review secret references before registering.')
