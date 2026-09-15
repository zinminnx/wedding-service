# EverAfter v14.0 - Security & Production Hardening

This milestone hardens the Django deployment without changing wedding business data or enabling destructive behavior.

## Added

- Opt-in production mode using `EVERAFTER_PRODUCTION=True`.
- Strict production secret and host validation.
- HTTPS redirect, secure cookies and HSTS controls.
- Trusted reverse-proxy support for Nginx/Cloudflare deployments.
- Request correlation IDs (`X-Request-ID`).
- Conservative browser security headers.
- No-store caching rules for authenticated dashboard/auth pages.
- Dependency-free cache-backed rate limiting for login, public invitation writes/reads and Local Print Agent APIs.
- Client IP values are hashed with HMAC before rate-limit keys/log messages; raw addresses and request bodies are not stored by this layer.
- `/health/live/` liveness endpoint.
- `/health/ready/` database readiness endpoint.
- `python manage.py production_check` deployment validator.
- Django system security checks when production mode is enabled.
- Example production environment, Nginx and systemd files under `deploy/`.
- Production security checklist.

## Important

Production hardening is **opt-in**. Installing this ZIP does not turn local development into HTTPS mode and does not modify firewall, DNS, Cloudflare, Nginx or aaPanel automatically.

The built-in rate limiter uses Django's configured cache. The current fallback is local-memory cache, which is appropriate for a single process/development. For a multi-worker/multi-server production deployment, configure a shared cache backend before relying on rate limits across workers.

## Install

Extract into the project root (same folder as `manage.py`):

```powershell
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Then:

```powershell
python manage.py runserver
```

Open:

- `http://127.0.0.1:8000/health/live/`
- `http://127.0.0.1:8000/health/ready/`

## Before production

Review `deploy/SECURITY_CHECKLIST.md` and `deploy/everafter.env.production.example`, then run:

```powershell
python manage.py production_check
python manage.py check --deploy
```

Do not enable HSTS preload until every relevant subdomain is permanently HTTPS.
