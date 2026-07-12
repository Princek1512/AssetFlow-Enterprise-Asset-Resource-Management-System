# AssetFlow — Full Stack (Backend + Frontend)

Complete combined project: FastAPI backend (Phase 1–4) and a React + Vite +
Tailwind frontend, strictly black/white/gray throughout.

## Structure

```
.
├── app/              FastAPI backend (see README.md for backend details)
├── requirements.txt
├── frontend/         React + Vite + Tailwind frontend
│   └── src/
│       ├── api/api.js              Axios client with auth interceptor
│       ├── context/AuthProvider.jsx
│       ├── components/             Sidebar, ProtectedRoute, Toast
│       └── pages/                  Dashboard, AssetDirectory, ResourceBooking,
│                                    Maintenance, TransferRequests,
│                                    AssetCategories, Admin, Login, Signup
└── README.md         Backend documentation (Phases 1–4)
```

## Running it

### 1. Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DB connection string, JWT secret, etc.
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`. First admin account is bootstrapped
automatically on startup from the `FIRST_ADMIN_*` settings in `.env`.

### 2. Frontend

```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
npm install
npm run dev
```

App runs at `http://localhost:5173`. Sign up as a new user (always created as
Employee), or log in with the bootstrapped admin account, to explore the
role-gated screens (Asset Categories and Admin are Admin/Asset-Manager-only;
Transfer Requests queue is Admin/Asset-Manager-only; everyone else can still
file a transfer request from the asset directory via the API).

## Notes

- The frontend calls the backend's real endpoints exactly as documented in the
  root `README.md`'s Phase 4 section — no mock data.
- All screens are wrapped in `ProtectedRoute`, which redirects unauthenticated
  users to `/login` and role-restricted pages back to `/` if the signed-in
  user's role doesn't qualify.
- Styling is deliberately restricted to Tailwind's default black/white/gray
  palette (see `frontend/tailwind.config.js`) — no other colors are used
  anywhere in the UI.
