# Backend Template Guide

This repository is a reusable FastAPI backend template for new products.

Use this guide to:
1. Start a new backend quickly.
2. Understand what is already included.
3. Customize the template safely for your own domain.

## What This Template Already Includes

- FastAPI app with versioned API routing (`/api/v1/...`).
- Layered architecture:
  - API endpoints (`app/api/v1/endpoints`)
  - Services (`app/services`)
  - Repositories (`app/repositories`)
  - Models and schemas (`app/models`, `app/schemas`)
  - Core infrastructure (`app/core`)
- Authentication foundations:
  - JWT session flow
  - Role-based access control (roles and permissions)
  - Password reset flow
  - 2FA endpoints (TOTP/SMS flow support)
- Async workers with Celery + RabbitMQ.
- Redis for sessions/cache.
- PostgreSQL with Alembic migrations.
- ELK stack services in Docker (`elasticsearch`, `logstash`, `kibana`).
- Nginx container for edge/proxy setup.
- Makefile commands for common development workflows.

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy (async) + AsyncPG
- Alembic
- Redis
- RabbitMQ + Celery + Flower
- PostgreSQL 15
- Docker Compose

## Quick Start

1. Copy env values.
```bash
cp .env.example .env
```
2. Start the local stack.
```bash
make up
```
3. Apply database migrations.
```bash
make migrate
```
4. Seed default admin and demo data.
```bash
make seed
make seed-permissions
```

## Local URLs

- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- Health: `http://localhost:8000/health`
- Flower: `http://localhost:5555`
- Kibana: `http://localhost:5601`
- PostgreSQL host port: `localhost:5433`

## Seeded Admin Account

Default seeded admin credentials:
- Email: `admin@example.com`
- Password: `Admin@123`

Important:
- Seed scripts now enable TOTP 2FA for admin users.
- `make seed` logs the admin TOTP secret so you can add it to Google Authenticator (or any TOTP app) before login verification.

## API Surface Included By Default

All routes are mounted under `/api/v1`.

- `/auth` for login and 2FA actions
- `/password` for forgot/reset/change flows
- `/roles` for role and permission management
- `/notifications` for notification operations
- `/admin` for admin user and audit operations
- `/users` for authenticated user profile actions

## Useful Make Commands

- `make up` / `make down` / `make restart`
- `make logs` / `make logs-api` / `make logs-db`
- `make migrate` / `make migrate-create` / `make migrate-rollback`
- `make seed` / `make seed-permissions`
- `make test` / `make coverage`
- `make lint` / `make format`

## Project Structure

```text
app/
  api/
  core/
  integrations/
  models/
  repositories/
  schemas/
  services/
  tasks/
alembic/
docker/
scripts/
tests/
```

## How To Use This As a GitHub Template

1. Push this repository to your GitHub organization.
2. Enable `Settings -> Template repository`.
3. Create new repos via `Use this template`.
4. For each new project:
```bash
git clone <new-repo-url>
cd <new-repo>
cp .env.example .env
make up
make migrate
make seed
make seed-permissions
```

## Customizations You Should Do For Every New Project

1. Product identity:
- Update `APP_NAME`, API descriptions, and ownership metadata.
- Replace placeholder secrets and external credentials in `.env`.

2. Domain modules:
- Keep generic modules.
- Replace/remove domain-specific integrations or workflows you do not need.
- Add your project-specific models, services, and endpoints.

3. Auth and access policy:
- Define your real role catalog and permissions.
- Update seed scripts for your org’s initial users/roles.
- Tune lockout/session/2FA policies in config.

4. Infrastructure profile:
- Keep only required services in `docker-compose.yml`.
- Adjust ports, memory limits, and health checks.
- Decide whether ELK is needed for local development.

5. Data model and migrations:
- Create project entities in `app/models` and `app/schemas`.
- Generate Alembic revisions with `make migrate-create`.
- Keep migrations small and reviewed.

6. Background jobs:
- Replace example Celery tasks with your own async workflows.
- Separate high-priority vs low-priority jobs if needed.

7. Quality and CI:
- Add/adjust tests in `tests/`.
- Enforce linting/type-checking in CI.
- Add deployment workflows and environment-specific gates.

## Recommended First Week Checklist For New Projects

1. Rename service and update environment defaults.
2. Remove unused integrations and example flows.
3. Define base domain entities and generate migrations.
4. Configure real auth roles and permission matrix.
5. Wire one core business endpoint end-to-end.
6. Add at least one integration and one background task.
7. Add integration tests for auth + one business path.
8. Finalize staging deployment pipeline.

## Troubleshooting Notes

- If migrations fail with host resolution errors, run migrations through the provided Makefile commands (they execute inside Docker where service hostnames resolve).
- If login returns `Login is only permitted for users with 2FA enabled.`, re-run `make seed` to ensure seeded admin 2FA fields are set.
- If role/permission seeding was partially run, `make seed-permissions` is idempotent and safe to rerun.

## Final Notes

Treat this repository as a strong starting point, not a fixed product. Keep shared conventions stable, but aggressively replace domain-specific examples with your own business logic.
