# B2B Supplier Platform

Modular FastAPI backend for cloud multi-tenancy or a single-company on-premise installation. PostgreSQL is the system of record.

## Start locally

1. Copy `.env.example` to `.env` and replace `JWT_SECRET_KEY`.
2. Run `docker compose up --build`.
3. Open `/docs` or call `/health`.

The API container applies `alembic upgrade head` before starting. For a host-side migration, set `DATABASE_URL` to your database and run `alembic upgrade head`.

## Data guarantees

- Every tenant-owned table has `company_id`; composite foreign keys prevent cross-company references.
- Application services derive `company_id` from the JWT claims and never accept it as a client-controlled filter.
- Inventory updates use `record_stock_movement()` inside one database transaction. The stock row is updated and ledgered together; database constraints prohibit negative available or reserved stock.
- Records that users deactivate retain history; customers, categories, products, and warehouses also have `deleted_at` for soft deletion.

## Project layout

Each domain package (`auth`, `orders`, `inventory`, etc.) will own its router, schemas, service layer, and repository queries. Shared configuration, database setup, and tenant-scoping stay in `app/core`. This deliberately remains a modular monolith.

## First-use flow

1. `POST /auth/bootstrap` creates the first company and its owner, returning a bearer token.
2. Use that token in `/docs` through **Authorize**.
3. Create users, customers, categories, products, warehouses, then record opening stock.
4. Create and confirm an order, fulfil it from a warehouse, create its invoice, then record payments.

`GET /audit-logs` is restricted to owners and admins. `GET/PUT /settings` manages tenant-specific JSON settings; writing a setting produces an audit event.

## Tests

Install the development dependencies and run `pytest`. The included smoke tests cover health and JWT claims. The next test layer should use an isolated PostgreSQL database to verify migrations, tenant boundaries, stock concurrency, and the order-to-payment workflow.
