# Docker Guide - AR_AS Recommendation System

Complete guide for building, deploying, and managing the AR_AS Recommendation System using Docker.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Building Images](#building-images)
- [Running Services](#running-services)
- [Health Checks](#health-checks)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)
- [Backup & Recovery](#backup--recovery)

## 🎯 Overview

The AR_AS system uses a **multi-container Docker architecture** with:

- **Multi-stage Dockerfile** for optimized image sizes
- **Docker Compose** for orchestrating all services
- **Health checks** for all critical services
- **Resource limits** to prevent resource exhaustion
- **Logging configuration** for ELK stack integration
- **Volume management** for data persistence

## 📦 Prerequisites

### Required Software

```bash
# Docker (version 20.10 or higher)
docker --version

# Docker Compose (version 2.0 or higher)
docker-compose --version

# Make (optional, for convenience commands)
make --version
```

### System Resources

Minimum requirements:
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 20 GB free space

Recommended for production:
- **CPU**: 8+ cores
- **RAM**: 16+ GB
- **Disk**: 50+ GB SSD

## 🚀 Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/TF-Jordan/AR_AS.git
cd AR_AS

# Copy environment file
cp .env.production .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

### 2. Start Everything (Using Make)

```bash
# Build, start, and initialize all services
make quickstart

# This will:
# - Build all Docker images
# - Start all services
# - Run database migrations
# - Initialize vector database
```

### 3. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Celery)**: http://localhost:5555
- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200

## 🏗 Architecture

### Service Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     AR_AS Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   API    │  │  Worker  │  │   Beat   │  │  Flower  │       │
│  │  :8000   │  │(Celery)  │  │(Scheduler)│  │  :5555   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘       │
│       │             │             │                             │
│       └─────────────┴─────────────┘                             │
│                     │                                           │
│    ┌────────────────┼────────────────┐                         │
│    │                │                │                         │
│ ┌──▼────┐    ┌─────▼────┐    ┌─────▼────┐                     │
│ │Postgres│    │  Redis   │    │  Qdrant  │                     │
│ │ :5432  │    │  :6379   │    │  :6333   │                     │
│ └────────┘    └──────────┘    └──────────┘                     │
│                                                                 │
│ ┌───────────────── Monitoring ─────────────────┐               │
│ │                                               │               │
│ │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │               │
│ │  │   ELK    │  │   APM    │  │Metricbeat│   │               │
│ │  │Kibana    │  │ Server   │  │          │   │               │
│ │  │ :5601    │  │  :8200   │  └──────────┘   │               │
│ │  └──────────┘  └──────────┘                  │               │
│ └───────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Docker Services

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| api | ar-as-api | 8000 | FastAPI application |
| celery-worker | ar-as-worker | - | Background task processor |
| celery-beat | ar-as-beat | - | Task scheduler |
| flower | ar-as-flower | 5555 | Celery monitoring |
| postgres | ar-as-postgres | 5432 | PostgreSQL database |
| redis | ar-as-redis | 6379 | Cache & message broker |
| qdrant | ar-as-qdrant | 6333 | Vector database |
| elasticsearch | ar-as-elasticsearch | 9200 | Log storage |
| logstash | ar-as-logstash | 5044 | Log processing |
| kibana | ar-as-kibana | 5601 | Log visualization |
| apm-server | ar-as-apm-server | 8200 | APM data collector |
| filebeat | ar-as-filebeat | - | Log shipper |
| metricbeat | ar-as-metricbeat | - | Metrics collector |

## ⚙️ Configuration

### Environment Variables

Create a `.env` file from `.env.production`:

```bash
cp .env.production .env
```

**Key variables to configure:**

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_random_secret_key_min_32_chars

# Flower (Celery UI)
FLOWER_USER=admin
FLOWER_PASSWORD=secure_password

# Kibana
KIBANA_ENCRYPTION_KEY=your_32_character_encryption_key
```

### Model Paths

Ensure ML models are in the correct directories:

```bash
# Sentiment model
models/distil-camembert-sentiment/

# Embedding model
models/paraphrase-multilingual-mpnet-base-v2/
```

## 🔨 Building Images

### Build All Images

```bash
# Using Make
make build

# Or using docker-compose directly
docker-compose build --parallel
```

### Build Without Cache

```bash
make build-no-cache
```

### Build Specific Service

```bash
docker-compose build api
docker-compose build celery-worker
```

## 🏃 Running Services

### Start All Services

```bash
# Using Make (recommended)
make up

# Or using docker-compose
docker-compose up -d
```

### Start Specific Services

```bash
# Start only database and cache
docker-compose up -d postgres redis

# Start only API
docker-compose up -d api
```

### View Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-worker
make logs-elk

# Or using docker-compose
docker-compose logs -f api
```

### Stop Services

```bash
# Stop all
make down

# Stop and remove volumes (WARNING: deletes all data)
make down-volumes
```

## 🏥 Health Checks

### Check Service Status

```bash
# Using Make
make status

# Or using docker-compose
docker-compose ps
```

### Manual Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health/live

# Elasticsearch health
curl http://localhost:9200/_cluster/health

# Postgres health
docker-compose exec postgres pg_isready -U postgres

# Redis health
docker-compose exec redis redis-cli ping
```

### Automated Health Check

```bash
make health
```

## 📊 Monitoring

### Access Monitoring Dashboards

```bash
# Kibana (logs & metrics)
make monitor-kibana
# or visit: http://localhost:5601

# Flower (Celery tasks)
make monitor-flower
# or visit: http://localhost:5555

# API metrics
make monitor-api
# or visit: http://localhost:8000/api/v1/metrics
```

### View Service Metrics

```bash
# Container resource usage
docker stats

# Detailed service info
docker-compose ps -a
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### 2. Out of Disk Space

```bash
# Clean up Docker resources
make clean

# Remove all unused Docker data
docker system prune -a --volumes
```

#### 3. Container Won't Start

```bash
# Check logs
docker-compose logs <service-name>

# Rebuild container
docker-compose up -d --build <service-name>
```

#### 4. Database Connection Issues

```bash
# Check if Postgres is running
docker-compose ps postgres

# Check logs
make logs-postgres

# Restart Postgres
docker-compose restart postgres
```

#### 5. Memory Issues

```bash
# Check resource limits in docker-compose.yml
# Adjust memory limits under deploy.resources.limits

# Example: Increase API memory limit
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G  # Increase from 2G
```

### Debug Mode

#### Access Container Shell

```bash
# API container
make shell-api

# Worker container
make shell-worker

# Database shell
make shell-postgres

# Redis shell
make shell-redis
```

#### Run Commands in Container

```bash
# Check Python version
docker-compose exec api python --version

# Run migrations manually
docker-compose exec api alembic upgrade head

# Test database connection
docker-compose exec api python -c "from src.database import engine; print(engine.url)"
```

## 🚀 Production Deployment

### Pre-deployment Checklist

- [ ] Update `.env` with production values
- [ ] Change all default passwords
- [ ] Set `DEBUG=false`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set strong `SECRET_KEY`
- [ ] Configure SSL/TLS
- [ ] Set up backup strategy
- [ ] Configure monitoring alerts
- [ ] Test disaster recovery procedures

### Deployment Steps

```bash
# 1. Build production images
docker-compose build --no-cache

# 2. Start services
docker-compose up -d

# 3. Run migrations
make migrate

# 4. Initialize vector database
make init-vectors

# 5. Verify health
make health

# 6. Monitor logs
make logs
```

### Resource Limits

Edit `docker-compose.yml` to adjust resources:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'      # Maximum CPU cores
      memory: 2G     # Maximum memory
    reservations:
      cpus: '0.5'    # Guaranteed CPU
      memory: 512M   # Guaranteed memory
```

### Scaling Workers

```bash
# Scale to 4 workers
docker-compose up -d --scale celery-worker=4

# Or edit docker-compose.yml:
services:
  celery-worker:
    deploy:
      replicas: 4
```

## 💾 Backup & Recovery

### Database Backup

```bash
# Create backup
make backup-db

# Backups are stored in: backups/db_YYYYMMDD_HHMMSS.sql.gz
```

### Database Restore

```bash
# Restore from backup
make restore-db FILE=backups/db_20240115_120000.sql.gz
```

### Vector Database Backup

```bash
# Create Qdrant snapshot
make backup-qdrant

# Snapshots are stored in Qdrant's snapshot directory
```

### Volume Backup

```bash
# Backup all volumes
docker run --rm \
  -v ar-as-postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres-data.tar.gz -C /data .
```

### Automated Backups

Add to crontab:

```bash
# Daily backups at 2 AM
0 2 * * * cd /path/to/AR_AS && make backup-db
```

## 🛠 Development Workflow

### Local Development

```bash
# Start in development mode
make dev

# This starts services with:
# - Hot reload enabled
# - Debug mode on
# - Mounted source code volumes
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run linters
make lint

# Format code
make format
```

### Database Migrations

```bash
# Create new migration
make migrate-create MESSAGE="add_new_table"

# Apply migrations
make migrate

# Rollback last migration
make migrate-rollback
```

## 📚 Useful Commands Reference

### Make Commands

```bash
make help              # Show all available commands
make build             # Build all images
make up                # Start all services
make down              # Stop all services
make restart           # Restart all services
make logs              # View all logs
make status            # Check service status
make health            # Run health checks
make migrate           # Run database migrations
make test              # Run tests
make backup-db         # Backup database
make clean             # Clean up Docker resources
make quickstart        # Quick start everything
```

### Docker Compose Commands

```bash
docker-compose build               # Build images
docker-compose up -d              # Start in detached mode
docker-compose down               # Stop and remove containers
docker-compose ps                 # List containers
docker-compose logs -f <service>  # Follow logs
docker-compose restart <service>  # Restart service
docker-compose exec <service> sh  # Access container shell
```

## 🔐 Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Change default passwords** - Especially for Postgres, Redis, Flower
3. **Use secrets management** - Consider HashiCorp Vault or AWS Secrets Manager
4. **Enable SSL/TLS** - Use reverse proxy (nginx) with Let's Encrypt
5. **Limit resource access** - Use Docker networks and firewalls
6. **Regular updates** - Keep base images and dependencies updated
7. **Scan images** - Use `docker scan` or Trivy for vulnerability scanning
8. **Non-root users** - All services run as non-root users

## 📈 Performance Optimization

### Image Size Optimization

- Multi-stage builds reduce final image size
- Only production dependencies in final images
- `.dockerignore` prevents unnecessary file copying

### Build Cache

```bash
# Use build cache
docker-compose build

# Cache from registry
docker-compose build --cache-from ar-as-api:latest
```

### Layer Caching

Order Dockerfile instructions from least to most frequently changing:
1. System dependencies
2. Python dependencies (requirements.txt)
3. Application code

## 📞 Support

For issues and questions:
- GitHub Issues: https://github.com/TF-Jordan/AR_AS/issues
- Documentation: See `docs/` directory

## 📄 License

See LICENSE file for details.
