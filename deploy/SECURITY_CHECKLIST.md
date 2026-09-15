# EverVow Production Security Checklist

Before setting `EVERAFTER_PRODUCTION=True`:

1. Put the real secrets in a server-only environment file. Never commit `.env`.
2. Generate a long random `DJANGO_SECRET_KEY` (50+ characters).
3. Set explicit production hostnames in `DJANGO_ALLOWED_HOSTS` (never `*`).
4. Set HTTPS origins in `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. Terminate TLS at Nginx/Cloudflare and forward `X-Forwarded-Proto`.
6. Set `EVERAFTER_TRUST_PROXY=True` only when requests really pass through your trusted proxy.
7. Run `python manage.py collectstatic` for production static files.
8. Run `python manage.py production_check` and `python manage.py check --deploy`.
9. Verify `/health/live/` and `/health/ready/` through the public HTTPS hostname.
10. Keep PostgreSQL and the Django/Gunicorn port private; expose only 80/443 publicly.
11. Keep OneDrive/Microsoft Graph client secrets server-side only.
12. Back up PostgreSQL and verify an EverVow Archive export before destructive retention operations.
13. Keep `EVERAFTER_HSTS_PRELOAD=False` until every subdomain is permanently HTTPS.
14. Review permissions for `.env`, uploaded media, archive files and service logs.
15. Update Django/Python/PostgreSQL/security patches on a controlled schedule.

## Useful commands

```bash
python manage.py check
python manage.py check --deploy
python manage.py production_check
python manage.py migrate
python manage.py collectstatic --noinput
```

The v14.0 patch does not open firewall ports, install Gunicorn/Nginx, change DNS,
or enable Cloudflare settings automatically. Those are deployment-host actions and
must be applied deliberately on the VPS.
