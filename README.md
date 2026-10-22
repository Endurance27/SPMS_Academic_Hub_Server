# SPMS Academic Hub

Backend application with layered architecture, authentication, role-based access control, and async processing.

## Features

- **Multi-Role Authentication**: Role-based access control (RBAC)
- **2FA Security**: TOTP and SMS support
- **Async Processing**: RabbitMQ + Celery for background tasks
- **Real-time Caching**: Redis for session management and caching
- **Comprehensive Logging**: ELK Stack integration
- **CI/CD Ready**: Docker, Nginx, PostgreSQL
- **Email Integration**: SMTP-based email dispatch
- **Audit Trails**: Complete audit logging system
- **Notifications**: In-app notification system

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- RabbitMQ 3+

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd SPMS_Academic_Hub_Server
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Install Dependencies

```bash
# For development
make dev-install

# For production
make install
```

### 4. Start Services with Docker

```bash
# Start all services
make up

# Initialize database
make init-db

# Run migrations
make migrate

# Seed initial data
make seed
make seed-permissions
```

## Security Features

### Authentication & Authorization

- JWT-based authentication with refresh tokens
- Role-Based Access Control (RBAC)
- Session management with Redis
- Token blacklisting on logout
- Account lockout after failed attempts

### Two-Factor Authentication

```python
# Enable TOTP 2FA
POST /api/v1/auth/2fa/setup
Response: {
    "secret": "BASE32SECRET",
    "qr_code": "base64_encoded_qr",
    "backup_codes": ["CODE1", "CODE2", ...]
}

# Verify 2FA code
POST /api/v1/auth/2fa/verify
Body: {"code": "123456"}
```

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one digit
- Bcrypt hashing with 12 rounds

## API Endpoints

### Authentication

```bash
POST   /api/v1/auth/login          # Login
POST   /api/v1/auth/logout         # Logout
POST   /api/v1/auth/refresh        # Refresh token
POST   /api/v1/auth/2fa/setup      # Setup 2FA
POST   /api/v1/auth/2fa/verify     # Verify 2FA
POST   /api/v1/auth/2fa/enable     # Enable 2FA
```

### Users

```bash
GET    /api/v1/users/me            # Get current user
PATCH  /api/v1/users/me            # Update current user
```

### Admin

```bash
POST   /api/v1/admin/users         # Create user
GET    /api/v1/admin/users         # List users
PATCH  /api/v1/admin/users/:id     # Update user
DELETE /api/v1/admin/users/:id     # Delete user
GET    /api/v1/admin/audit-logs    # View audit logs
```

### Roles & Permissions

```bash
POST   /api/v1/roles               # Create role
GET    /api/v1/roles               # List roles
PATCH  /api/v1/roles/:id           # Update role
DELETE /api/v1/roles/:id           # Delete role
```

### Notifications

```bash
GET    /api/v1/notifications       # List notifications
PATCH  /api/v1/notifications/:id  # Mark as read
```

### Password

```bash
POST   /api/v1/password/forgot    # Request password reset
POST   /api/v1/password/reset     # Reset password
POST   /api/v1/password/change    # Change password
```

## Testing

### Run All Tests

```bash
make test
```

### Run with Coverage

```bash
make coverage
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit -v

# Integration tests only
pytest tests/integration -v

# Specific test file
pytest tests/unit/test_services/test_auth_service.py -v
```

## Celery Tasks

### Background Tasks

```python
# Start Celery worker
make celery-worker

# Start Celery beat (scheduler)
make celery-beat

# Monitor with Flower
make flower
# Access: http://localhost:5555
```

## Database Migrations

### Create Migration

```bash
alembic revision --autogenerate -m "Add new table"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Deployment

### Development

```bash
docker-compose up
```

### Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Environment Variables

Critical production environment variables:

```env
APP_ENV=production
DEBUG=False
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://:password@host:6379/0
```

### Health Checks

```bash
# API Health
curl http://localhost:8000/health

# Database Health
docker-compose exec postgres pg_isready

# Redis Health
docker-compose exec redis redis-cli ping
```

## Monitoring

### Flower (Celery Monitoring)

Access Flower at `http://localhost:5555` to:
- Monitor task execution
- View task history
- Inspect workers
- Manage task queues

### Kibana Dashboard

Access Kibana at `http://localhost:5601` to view:
- Application logs
- Error tracking
- Performance metrics
- User activity

## Security Best Practices

1. **Environment Variables**: Never commit `.env` files
2. **Secrets Management**: Use secret management services in production
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Configured per endpoint
5. **Input Validation**: Pydantic schemas validate all inputs
6. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
7. **XSS Protection**: FastAPI auto-escapes outputs
8. **CORS**: Configure allowed origins properly

## API Documentation

### Swagger UI

Access interactive API docs at:
```
http://localhost:8000/api/v1/docs
```

### ReDoc

Alternative API documentation:
```
http://localhost:8000/api/v1/redoc
```

## Default Credentials (Development)

Default seeded admin credentials:
- Email: `admin@example.com`
- Password: `Admin@123`

**Important**: Change default passwords in production!

## Useful Make Commands

- `make up` / `make down` / `make restart`
- `make logs` / `make logs-api` / `make logs-db`
- `make migrate` / `make migrate-create` / `make migrate-rollback`
- `make seed` / `make seed-permissions`
- `make test` / `make coverage`
- `make lint` / `make format`

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U app_user -d app_db
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# View Redis keys
docker-compose exec redis redis-cli keys "*"
```

### Celery Worker Issues

```bash
# Check worker status
docker-compose ps celery_worker

# View worker logs
docker-compose logs celery_worker

# Restart workers
docker-compose restart celery_worker celery_beat
```

### Migration Issues

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Rollback and reapply
alembic downgrade -1
alembic upgrade head
```

## Project Structure

```text
app/
  api/              # API endpoints
  core/             # Core functionality (config, security, database)
  integrations/     # External service integrations
  models/           # Database models
  repositories/     # Data access layer
  schemas/          # Pydantic schemas
  services/         # Business logic
  tasks/            # Celery tasks
alembic/            # Database migrations
docker/             # Docker configuration
scripts/            # Utility scripts
tests/              # Test suite
```

## Contributing

1. Create feature branch (`git checkout -b feature/amazing-feature`)
2. Commit changes (`git commit -m 'Add amazing feature'`)
3. Push to branch (`git push origin feature/amazing-feature`)
4. Open Pull Request

### Code Quality

Before submitting PR:

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test
```

## Support

For issues and questions, please open an issue on the repository..
