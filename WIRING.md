# Wiring it into your app

1. Copy `app/security.py` into your `app/` folder. If you already have `app/__init__.py`, leave it alone.
2. In the file that defines your webhook route, add the dependency:

```python
from fastapi import APIRouter, Depends
from app.security import require_github_signature

router = APIRouter()

@router.post("/webhook", dependencies=[Depends(require_github_signature)])
async def handle_webhook(...):
    ...
```

(Keep your existing route path and handler. Only add `dependencies=[...]`.)

3. In `docker-compose.yml`, add this line under `app: environment:`
```
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
```
4. Add `.env.example` to the repo root, and make sure `.env` is in `.gitignore`.
5. Copy `tests/test_security.py`, `requirements-dev.txt`, and `.github/workflows/tests.yml`.
6. If your handler reads the request body itself with `await request.json()` or a Pydantic model, that still works. The dependency reads the raw bytes first and Starlette caches them.
