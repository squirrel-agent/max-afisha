# Deployment

## Local / evaluator

```bash
cp .env.example .env
docker compose up --build
```

Only PostgreSQL+pgvector, backend, parser-service and frontend are started. Stop with `docker compose down`; restart with `docker compose up`.

## External / MAX

For a real MAX check:

1. Set strong `POSTGRES_PASSWORD` and `ADMIN_TOKEN`.
2. Set `MAX_BOT_TOKEN` in backend environment only.
3. Publish frontend/backend through HTTPS reverse proxy or a platform with HTTPS.
4. Restrict `CORS_ORIGINS` to the production frontend origin.
5. Attach the mini-app HTTPS URL to the issued MAX bot in platform settings.
6. Put the final bot/mini-app link and public API HTTPS address into the submission presentation.

Do not commit production `.env`, working tokens or passwords.

## Build-time considerations

- Backend uses CPU-only PyTorch and pinned `uv` installer.
- Frontend dependencies are exact versions and production build is multi-stage.
- Parser installs one Chromium runtime because it is required for dynamic sources; runtime browser instances are reused within a parse pass.
- There is no Redis or other unused service.

Initial base-image/model downloads depend on network/cache. No intentional build-time data scraping is performed.
