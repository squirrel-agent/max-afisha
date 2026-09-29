# API

Статический OpenAPI 3.1: `../openapi.yaml`. Runtime schema FastAPI: `/openapi.json`, Swagger: `/docs`.

Основные public endpoints:

- `GET /health`;
- `GET /api/cities`;
- `GET /api/events`, `GET /api/events/{id}`;
- `POST /api/users`;
- `PUT /api/users/{id}/city`;
- `PUT /api/users/{id}/preferences`;
- `POST /api/users/{id}/interactions`;
- `GET /api/recommendations/{id}`;
- `POST /api/recommendations/{id}/rating`;
- `POST /api/search/neural`;
- `GET /api/feed`;
- `POST /api/max/session` — server-side MAX initData validation;
- `GET /api/ml/status`;
- `GET /api/sources/status`.

Operational endpoints require `Authorization: Bearer <ADMIN_TOKEN>`:

- `POST /api/admin/ingest`;
- `POST /api/admin/parser/run`;
- `POST /api/dev/seed`;
- `POST /api/ml/embed-events`;
- `POST /api/sources/{source}/sync`.

`DATA-API.yaml` describes a minimal reproducible check sequence. Endpoints that need a real MAX-signed payload are not part of the Docker-local mandatory check, because fabricating MAX initData would violate the point of the signature validation.
