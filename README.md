# Backend Service Template

A reusable, production-ready FastAPI backend starter with layered architecture, auth/RBAC foundations, async workers, and infrastructure defaults.

## Template Setup Guide

If you want to use this architecture as a reusable starter for future projects, follow:

- `TEMPLATE_README.md` for the end-to-end template workflow
- `.env.example` for environment variable setup

## Domain-Specific Notes

Some modules in this bootstrap are domain examples (for example, parts of `app/integrations` and vetting/report workflows). Keep what you need and replace/remove the rest for your product domain.

## 🚀 Features

- **Multi-Role Authentication**: Administrator, Client, and Applicant roles with RBAC
- **2FA Security**: SMS and Google Authenticator support
- **Async Processing**: RabbitMQ + Celery for background tasks
- **Real-time Caching**: Redis for session management and caching
- **External Integrations**:
  - Pluggable third-party adapters (included examples can be replaced)
  - Identity/verification API integration pattern
  - Geocoding/location API integration pattern
- **Automated Report Generation**: PDF reports with executive summaries
- **Comprehensive Logging**: ELK Stack integration
- **CI/CD**: GitHub Actions for automated testing and deployment
- **Production Ready**: Docker, Nginx, PostgreSQL

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- RabbitMQ 3+

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/backend-template.git
cd backend-template
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
```


## 🔐 Security Features

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

## 📊 API Endpoints

### Authentication

```bash
POST   /api/v1/auth/login          # Login
POST   /api/v1/auth/logout         # Logout
POST   /api/v1/auth/refresh        # Refresh token
POST   /api/v1/auth/2fa/setup      # Setup 2FA
POST   /api/v1/auth/2fa/verify     # Verify 2FA
POST   /api/v1/auth/2fa/enable     # Enable 2FA
```

### Applications

```bash
POST   /api/v1/applications        # Create application
GET    /api/v1/applications        # List applications
GET    /api/v1/applications/:id    # Get application details
PATCH  /api/v1/applications/:id    # Update application
POST   /api/v1/applications/:id/submit  # Submit for processing
POST   /api/v1/applications/:id/documents # Upload documents
```

### Reports

```bash
GET    /api/v1/reports/:id         # Get report
GET    /api/v1/reports/:id/pdf     # Download PDF
POST   /api/v1/reports/:id/generate # Generate report
```

### Admin

```bash
POST   /api/v1/admin/users         # Create user
GET    /api/v1/admin/users         # List users
PATCH  /api/v1/admin/users/:id     # Update user
DELETE /api/v1/admin/users/:id     # Delete user
POST   /api/v1/admin/clients       # Create client
GET    /api/v1/admin/audit-logs    # View audit logs
```

## 🧪 Testing

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

### Test Database

Tests use a separate test database configured in `conftest.py`:

- Database: `test_db`
- Redis DB: `1` (separate from production)

## 🔄 Celery Tasks

### Background Check Tasks

```python
# Start Celery worker
make celery-worker

# Start Celery beat (scheduler)
make celery-beat

# Monitor with Flower
make flower
# Access: http://localhost:5555
```

### Task Types

1. **check_ghana_card** - Verify Ghana Card with NIA
2. **check_credit_history** - Credit check via XDS Data
3. **geocode_addresses** - Geocode addresses using Google Maps
4. **verify_employment** - Verify employment history
5. **verify_education** - Verify education credentials
6. **generate_report** - Generate final PDF report

## 📝 Database Migrations

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

## 🚢 Deployment

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

## 📊 Monitoring

### Prometheus Metrics

Metrics exposed at `/metrics`:

- Request count
- Request duration
- Active sessions
- Task queue length

### Kibana Dashboard

Access Kibana at `http://localhost:5601` to view:

- Application logs
- Error tracking
- Performance metrics
- User activity

### Flower (Celery Monitoring)

Access Flower at `http://localhost:5555` to:

- Monitor task execution
- View task history
- Inspect workers
- Manage task queues

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit `.env` files
2. **Secrets Management**: Use secret management services in production
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Configured per endpoint
5. **Input Validation**: Pydantic schemas validate all inputs
6. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
7. **XSS Protection**: FastAPI auto-escapes outputs
8. **CORS**: Configure allowed origins properly

## 📚 API Documentation

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

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

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



## 🆘 Support

For issues and questions:

- **Issues**: GitHub Issues
<!-- - **Email**: support@backend-template.com
- **Documentation**: [docs.backend-template.com](https://docs.backend-template.com) -->

## 🎯 Roadmap

### Phase 1 (Current)

- ✅ Core authentication system
- ✅ Application management
- ✅ Background checks integration
- ✅ Report generation

### Phase 2

- [ ] Mobile application (React Native)
- [ ] Real-time notifications (WebSockets)
- [ ] Advanced analytics dashboard
- [ ] Bulk processing

### Phase 3

- [ ] AI-powered risk assessment
- [ ] Blockchain verification
- [ ] Multi-tenant architecture
- [ ] International expansion

## 📞 Default Credentials (Development)



## 🏁 Quick Start Guide

### For Developers

```bash
# 1. Clone and setup
git clone https://github.com/your-org/backend-template.git
cd backend-template
cp .env.example .env

# 2. Start services
make up

# 3. Initialize database
make init-db
make migrate
make seed

# 4. Run tests
make test

# 5. Access application
# API: http://localhost:8000
# Docs: http://localhost:8000/api/v1/docs
# Flower: http://localhost:5555
# Kibana: http://localhost:5601
```

### For Production Deployment

```bash
# 1. Configure production environment
cp .env.example .env.production
# Edit .env.production with production values

# 2. Build and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 3. Initialize production database
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
docker-compose -f docker-compose.prod.yml exec api python scripts/seed_data.py

# 4. Verify deployment
curl https://your-domain.com/health
```

## 🔧 Troubleshooting

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
