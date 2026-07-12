<<<<<<< HEAD
# AssetFlow — Phase 1 + Phase 2 + Phase 3 + Phase 4
=======
# AssetFlow — Phase 1 + Phase 2
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9

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

<<<<<<< HEAD
## What's implemented in Phase 3

### Direct allocation — double-allocation prevention (`app/api/v1/assets.py`)
- `POST /api/v1/assets/{id}/allocate` — **Admin / Asset Manager**, assigns a
  non-bookable asset to an employee. Row-locks the asset with `SELECT ... FOR UPDATE`
  for the whole transaction so two concurrent allocation attempts against the same
  asset can never both succeed. If the asset is already held by someone else, this
  does **not** silently fail — it returns `409` with the current holder's id and a
  hint to use the transfer-request flow instead of a rejected write.
- `POST /api/v1/assets/{id}/release` — **Admin / Asset Manager**, clears the holder
  and returns the asset to `available` (also row-locked, also state-machine-validated).
- Bookable assets (`is_bookable=true`) are rejected from this endpoint with `422` —
  they go through the Booking flow below instead.

### Transfer requests — the conflict-resolution path (`app/api/v1/assets.py`,
`app/api/v1/transfer_requests.py`)
- `POST /api/v1/assets/{id}/transfer-requests` — any authenticated user can request
  an already-allocated asset be reassigned to them instead of hitting a dead end.
- `GET /api/v1/transfer-requests` / `GET /api/v1/transfer-requests/{id}` —
  **Admin / Asset Manager**, filterable by `status` and `asset_id`.
- `POST /api/v1/transfer-requests/{id}/approve` — **Admin / Asset Manager**. Row-locks
  both the request and the underlying asset, re-verifies the asset's holder hasn't
  changed since the request was filed (auto-rejecting the request with `409` if it
  has), reassigns `current_holder_id`, and auto-rejects any other still-pending
  requests for the same asset since they'd now be stale.
- `POST /api/v1/transfer-requests/{id}/reject` — **Admin / Asset Manager**.

### Bookings — time-slot overlap validation (`app/api/v1/bookings.py`)
- `POST /api/v1/bookings` — books a `is_bookable=true` resource for a time window.
  The resource (Asset) row is locked with `SELECT ... FOR UPDATE` for the whole
  transaction, which serializes every concurrent booking attempt against the same
  resource — the second of two racing requests always sees the first request's
  just-committed row, so an overlapping double-booking can never slip through. Any
  authenticated user books for themselves; Admin / Asset Manager may pass `employee_id`
  to book on someone else's behalf. Overlaps return `409` with the conflicting booking.
- `GET /api/v1/bookings` — the shared calendar, visible to any authenticated user
  (filterable by `resource_id`, `employee_id`, `status`), so people can see what's
  booked before they even try — not just have the server reject a clash after the fact.
- `GET /api/v1/bookings/{id}` — single booking detail.
- `POST /api/v1/bookings/{id}/cancel` — the booking's own employee, or Admin / Asset
  Manager, may cancel it. Validated through the same generic `StateMachine` introduced
  in Phase 2 (`app/services/booking_lifecycle.py`) — `completed`/`cancelled` are
  terminal, so a stale cancel attempt returns `409` instead of corrupting state.

=======
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
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
<<<<<<< HEAD
- **Phase 4** — Maintenance request routing (approval flips status to `under_maintenance`
  via the asset state machine, using the same `StateMachine` primitive as bookings) +
  dashboard KPI aggregations (utilization rates, overdue maintenance, booking load per
  resource) + the time-driven `upcoming → ongoing → completed` booking sweep noted in
  `app/services/booking_lifecycle.py`.

Reply **"proceed to Phase 4"** when ready.

## Phase 3 smoke test

```bash
# Register a non-bookable asset (e.g. a laptop) and a bookable one (e.g. a meeting room)
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Conference Room A", "category_id": "<ROOM_CATEGORY_ID>", "is_bookable": true}'

# Allocate the laptop to an employee
curl -X POST http://localhost:8000/api/v1/assets/{laptop_id}/allocate \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" -H "Content-Type: application/json" \
  -d '{"employee_id": "<EMPLOYEE_ID>"}'

# A second allocation attempt is rejected with the current holder, not a silent failure
curl -X POST http://localhost:8000/api/v1/assets/{laptop_id}/allocate \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" -H "Content-Type: application/json" \
  -d '{"employee_id": "<ANOTHER_EMPLOYEE_ID>"}'
# -> 409 { "current_holder_id": "...", "hint": "Use POST .../transfer-requests ..." }

# That other employee requests a transfer instead
curl -X POST http://localhost:8000/api/v1/assets/{laptop_id}/transfer-requests \
  -H "Authorization: Bearer <ANOTHER_EMPLOYEE_TOKEN>" -H "Content-Type: application/json" \
  -d '{"reason": "Need it for a client demo next week"}'

# Admin approves — the asset flips holder atomically
curl -X POST http://localhost:8000/api/v1/transfer-requests/{transfer_request_id}/approve \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" -H "Content-Type: application/json" -d '{}'

# Book the meeting room for a slot
curl -X POST http://localhost:8000/api/v1/bookings \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" -H "Content-Type: application/json" \
  -d '{"resource_id": "<ROOM_ID>", "start_time": "2026-07-15T09:00:00Z", "end_time": "2026-07-15T10:00:00Z"}'

# A second, overlapping booking on the same room is rejected
curl -X POST http://localhost:8000/api/v1/bookings \
  -H "Authorization: Bearer <ANOTHER_EMPLOYEE_TOKEN>" -H "Content-Type: application/json" \
  -d '{"resource_id": "<ROOM_ID>", "start_time": "2026-07-15T09:30:00Z", "end_time": "2026-07-15T10:30:00Z"}'
# -> 409 { "message": "This resource is already booked for an overlapping time slot.", ... }
```

---

## Phase 4 additions (Maintenance & Dashboard)

Adds the maintenance-request workflow and the fleet-wide dashboard on top of the
Phase 3 backend, reusing the existing `StateMachine`, `require_role`, and
row-locking conventions rather than introducing new patterns.

**New endpoints:**
- `POST   /api/v1/maintenance` — report an asset issue (any authenticated user)
- `GET    /api/v1/maintenance` — list maintenance requests (filter by `asset_id`, `status`)
- `GET    /api/v1/maintenance/{request_id}` — get a single request
- `PATCH  /api/v1/maintenance/{request_id}/status` — drive the workflow forward
  (Admin / Asset Manager only): `pending -> approved -> in_progress -> completed`,
  or `pending -> rejected`. Automatically flips the linked Asset's status
  (`under_maintenance` while approved/in-progress, back to `available` on completion).
- `GET    /api/v1/dashboard/kpis` — active assets, assets allocated, maintenance in
  progress, and active bookings counts (any authenticated role)
- `GET    /api/v1/dashboard/overdue-returns` — bookings still `ongoing` past their
  `end_time`

**New files:**
- `app/schemas/maintenance.py`, `app/schemas/dashboard.py`
- `app/services/maintenance_lifecycle.py`, `app/services/dashboard_analytics.py`
- `app/api/v1/maintenance.py`, `app/api/v1/dashboard.py`

Both routers are wired into `app/main.py`, and the app version has been bumped to
`0.4.0`.
=======
- **Phase 3** — Allocation double-booking lock (`SELECT ... FOR UPDATE` on `current_holder_id`)
  + Booking time-slot overlap validation for shared/bookable resources.
- **Phase 4** — Maintenance request routing (approval flips status to `under_maintenance`
  via the state machine above) + Transfer Request workflow + dashboard KPI aggregations.

Reply **"proceed to Phase 3"** when ready.
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
