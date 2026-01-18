# 🚀 Docker Quick Start Guide

Get the AR_AS Recommendation System up and running in minutes!

## ⚡ Super Quick Start

```bash
# 1. Copy environment file
cp .env.production .env

# 2. Start everything (build + run + initialize)
make quickstart

# 3. Access the system
# API:     http://localhost:8000/docs
# Flower:  http://localhost:5555
# Kibana:  http://localhost:5601
```

## 📋 What's Included?

When you run `make quickstart`, you get:

- ✅ **FastAPI Application** (port 8000)
- ✅ **Celery Workers** for background tasks
- ✅ **PostgreSQL Database** (port 5432)
- ✅ **Redis Cache** (port 6379)
- ✅ **Qdrant Vector DB** (port 6333)
- ✅ **ELK Stack** for monitoring (Kibana on 5601)
- ✅ **APM Server** for tracing
- ✅ **Flower** for task monitoring (port 5555)

## 🛠 Common Commands

### Starting/Stopping

```bash
make up       # Start all services
make down     # Stop all services
make restart  # Restart all services
```

### Monitoring

```bash
make logs           # View all logs
make logs-api       # View API logs only
make logs-worker    # View worker logs
make status         # Check service status
make health         # Run health checks
```

### Database

```bash
make migrate        # Run database migrations
make backup-db      # Backup database
make shell-postgres # Access PostgreSQL shell
```

### Development

```bash
make test       # Run tests
make lint       # Run linters
make format     # Format code
make shell-api  # Access API container shell
```

## 🔧 Configuration

Before starting, edit `.env` file and change:

```bash
# Security (IMPORTANT!)
POSTGRES_PASSWORD=your_secure_password
SECRET_KEY=your_random_secret_key_min_32_chars
FLOWER_PASSWORD=secure_password
KIBANA_ENCRYPTION_KEY=your_32_character_key

# Model paths (ensure models exist)
SENTIMENT_MODEL_PATH=./models/distil-camembert-sentiment
EMBEDDING_MODEL_PATH=./models/paraphrase-multilingual-mpnet-base-v2
```

## 📊 Access Points

After startup, access these URLs:

| Service | URL | Description |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| API | http://localhost:8000 | Main API endpoint |
| Flower | http://localhost:5555 | Celery task monitor |
| Kibana | http://localhost:5601 | Logs & metrics dashboard |
| Elasticsearch | http://localhost:9200 | Search & analytics |

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find and kill process using port 8000
lsof -i :8000
kill -9 <PID>
```

### Services Won't Start

```bash
# Check logs
make logs

# Restart specific service
docker-compose restart api
```

### Out of Memory

```bash
# Increase Docker memory limit in Docker Desktop
# Settings → Resources → Memory → 8GB+
```

### Clean Start

```bash
# Stop everything and remove volumes
make down-volumes

# Clean Docker resources
make clean

# Rebuild and start fresh
make quickstart
```

## 📈 Resource Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB

**Recommended:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 50+ GB SSD

## 📚 Full Documentation

For detailed documentation, see:
- [Complete Docker Guide](docs/DOCKER.md)
- [Monitoring Guide](monitoring/README.md)
- [API Documentation](http://localhost:8000/docs) (after startup)

## ❓ Need Help?

```bash
# Show all available make commands
make help

# View service status
make status

# Check service health
make health

# View API logs
make logs-api
```

## 🔒 Security Notes

**Before deploying to production:**

1. ✅ Change all default passwords in `.env`
2. ✅ Set `DEBUG=false`
3. ✅ Configure proper `CORS_ORIGINS`
4. ✅ Use strong `SECRET_KEY`
5. ✅ Enable SSL/TLS
6. ✅ Set up regular backups

## 🎯 Next Steps

After quick start:

1. **Test the API** - Visit http://localhost:8000/docs
2. **Monitor tasks** - Check http://localhost:5555
3. **View logs** - Open http://localhost:5601
4. **Run tests** - Execute `make test`
5. **Read docs** - See `docs/` directory

---

**Happy Coding! 🚀**
