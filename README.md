# AssetFlow — Phase 1 + Phase 2

## Stack
- **FastAPI** (async) — rapid API generation, auto-generated OpenAPI docs at `/docs`
- **SQLAlchemy 2.0 (async, asyncpg driver)** — ORM with explicit row-locking support
  (`SELECT ... FOR UPDATE`), required for Phase 3's double-allocation / booking-overlap rules
- **PostgreSQL** — relational integrity, native enum types, JSONB for category metadata
- **python-jose** — JWT issuance/verification
- **passlib[bcrypt]** — password hashing

## What's implemented in Phase 1

### Full schema (ORM models, `app/models/`)
All core entities are modeled now so later phases don't require migrations rework:
`User`, `Department`, `AssetCategory`, `Asset`, `Booking`, `MaintenanceRequest`,
`TransferRequest`. Enums (`app/models/enums.py`) map to native Postgres enum types
for `role`, department `status`, asset `condition`/`status`, booking `status`,
maintenance `priority`/`status`, and transfer-request `status`.

### Auth & RBAC (`app/api/v1/auth.py`, `app/api/v1/admin.py`)
- `POST /api/v1/auth/signup` — public signup, **always** creates an `employee` role account
- `POST /api/v1/auth/login` — OAuth2-password-flow login, returns a JWT bearer token
- `GET /api/v1/auth/me` — current authenticated user's profile
- `GET /api/v1/admin/users` — **Admin-only**, lists all users (org management panel)
- `POST /api/v1/admin/users/{user_id}/promote` — **Admin-only**, promotes/demotes a user's
  role (`asset_manager`, `department_head`, or back to `employee`). Row is locked with
  `SELECT ... FOR UPDATE` for the transaction to prevent race conditions on concurrent
  promotion requests against the same user.
- `PATCH /api/v1/admin/users/{user_id}/deactivate` — **Admin-only**, deactivates an account

RBAC is enforced via the `require_role(*roles)` dependency factory in `app/core/deps.py`,
which decodes the JWT, loads the user, and 403s if their role isn't in the allowed set.

### First Admin bootstrap
Since signup only ever creates Employees, and promotion requires an existing Admin,
the app seeds one Admin account on startup from `FIRST_ADMIN_EMAIL` /
`FIRST_ADMIN_PASSWORD` in your `.env` — but only if no Admin exists yet.

## What's implemented in Phase 2

### Asset lifecycle state machine (`app/core/state_machine.py`, `app/services/asset_lifecycle.py`)
A generic, reusable `StateMachine` class wraps a `{state: {allowed_next_states}}` map and
raises `InvalidTransitionError` on illegal moves. It's deliberately not asset-specific —
Phase 4's `MaintenanceRequest` / `TransferRequest` / `Booking` status workflows should reuse
the same primitive instead of hand-rolling their own if/else checks. The Asset-specific
transition map lives in `app/services/asset_lifecycle.py`:

```
available          -> allocated, reserved, under_maintenance, lost, retired
allocated          -> available, under_maintenance, lost
reserved           -> available, allocated, under_maintenance
under_maintenance  -> available, retired, disposed, lost
lost               -> available, retired, disposed
retired            -> disposed
disposed           -> (terminal — no further transitions)
```

### Asset Category CRUD (`app/api/v1/asset_categories.py`)
- `POST /api/v1/asset-categories` — **Admin / Asset Manager**, create a category
  (supports free-form `custom_fields` JSONB for per-category metadata schemas)
- `GET /api/v1/asset-categories` / `GET /api/v1/asset-categories/{id}` — any authenticated user
- `PATCH /api/v1/asset-categories/{id}` — **Admin / Asset Manager**
- `DELETE /api/v1/asset-categories/{id}` — **Admin / Asset Manager**; blocked with `409` if any
  assets still reference the category (FK is `ON DELETE RESTRICT`)

### Asset registration & directory (`app/api/v1/assets.py`)
- `POST /api/v1/assets` — **Admin / Asset Manager**, registers a new asset. `asset_tag`
  (e.g. `AF-0001`) is **never** client-supplied — it's pulled from a real Postgres sequence
  (`asset_tag_seq`, defined in `app/models/asset.py`) so concurrent registrations can't collide
  or race on the tag, with no row lock needed. New assets always start at `status=available`.
- `GET /api/v1/assets` — directory listing for any authenticated user, with optional
  `status`, `category_id`, `is_bookable`, and free-text `search` (name/tag/serial) filters,
  plus `skip`/`limit` pagination.
- `GET /api/v1/assets/{id}` — single asset detail
- `PATCH /api/v1/assets/{id}` — **Admin / Asset Manager**, edits directory metadata
  (name, category, serial number, condition, location, bookable flag). Deliberately does
  **not** accept `status` — see below.
- `POST /api/v1/assets/{id}/status` — **Admin / Asset Manager**, the *only* way to change an
  asset's status. Row-locks the asset with `SELECT ... FOR UPDATE` (same pattern as the
  Phase 1 promote/deactivate endpoints) so two concurrent transition requests can't race,
  then validates the move against the state machine above before committing. Illegal
  transitions return `409` with the allowed next states in the error detail.

## Running locally

```bash
# 1. Create and activate a virtualenv
python3 -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# edit .env: set DATABASE_URL to your local Postgres instance, and a real SECRET_KEY

# 4. Make sure Postgres is running and the database in DATABASE_URL exists, e.g.:
#    createdb assetflow

# 5. Run the API
uvicorn app.main:app --reload
```

Then open **http://localhost:8000/docs** for interactive Swagger docs.

> **Note on migrations:** for hackathon speed, `app/main.py` calls
> `Base.metadata.create_all` on startup, which creates all tables directly from the
> ORM models — no migration step needed to get running. A minimal Alembic setup can
> be dropped in later if you need real migration history; the models are already
> structured to support that without changes.

## Quick smoke test

```bash
# Sign up (creates an Employee)
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Jane Doe", "email": "jane@company.com", "password": "SecurePass123"}'

# Log in (OAuth2 form fields: username=email, password=password)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=jane@company.com&password=SecurePass123"

# Log in as the bootstrapped Admin, then promote Jane
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@assetflow.local&password=ChangeMe123!"

curl -X POST http://localhost:8000/api/v1/admin/users/{jane_user_id}/promote \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"role": "asset_manager"}'
```

## Phase 2 smoke test

```bash
# Create a category (Admin / Asset Manager token required)
curl -X POST http://localhost:8000/api/v1/asset-categories \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptops", "description": "Employee laptops"}'

# Register an asset — asset_tag is generated server-side (AF-0001, ...)
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Dell XPS 15", "category_id": "<CATEGORY_ID>", "serial_number": "SN12345", "condition": "new"}'

# Browse the directory
curl "http://localhost:8000/api/v1/assets?status=available&limit=20" \
  -H "Authorization: Bearer <ANY_ACCESS_TOKEN>"

# Send it for maintenance — a guarded, state-machine-validated transition
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/status \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"status": "under_maintenance", "reason": "Screen flickering"}'

# Illegal transition (e.g. disposed -> available) returns 409 with allowed next states
```

## What's next
- **Phase 3** — Allocation double-booking lock (`SELECT ... FOR UPDATE` on `current_holder_id`)
  + Booking time-slot overlap validation for shared/bookable resources.
- **Phase 4** — Maintenance request routing (approval flips status to `under_maintenance`
  via the state machine above) + Transfer Request workflow + dashboard KPI aggregations.

Reply **"proceed to Phase 3"** when ready.
