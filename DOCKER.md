# Guide Docker - AR_AS

Guide complet pour la conteneurisation du projet AR_AS avec options modulaires.

## Architecture des Profils

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PROFILS DISPONIBLES                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  module4      API Module 4 uniquement (Livreur Ranking)                 │
│               → Image ~200 MB                                            │
│               → Démarrage ~5 secondes                                    │
│               → Sans dépendances externes                                │
│                                                                          │
│  full         Système complet (Modules 1, 2, 3, 4)                      │
│               → Image ~4 GB (inclut torch + transformers)                │
│               → Nécessite PostgreSQL, Redis, Qdrant                      │
│               → Celery workers pour tâches async                         │
│                                                                          │
│  monitoring   Stack ELK (Elasticsearch, Kibana, APM)                    │
│               → Optionnel, pour la production                            │
│               → Dashboards pré-configurés                                │
│                                                                          │
│  dev          Développement Module 4 (hot-reload)                       │
│                                                                          │
│  dev-full     Développement complet (hot-reload + toutes les BDD)       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Commandes Rapides

### Module 4 Uniquement (Recommandé pour commencer)

```bash
# Production - Module 4 seul
docker compose --profile module4 up -d

# Vérifier le statut
docker compose --profile module4 ps

# Voir les logs
docker compose --profile module4 logs -f

# Arrêter
docker compose --profile module4 down
```

**Accès:** http://localhost:8000/docs

### Système Complet

```bash
# Production - Tous les modules
docker compose --profile full up -d

# Avec monitoring ELK
docker compose --profile full --profile monitoring up -d

# Arrêter
docker compose --profile full down
```

### Développement

```bash
# Dev Module 4 (hot-reload)
docker compose --profile dev up

# Dev complet (hot-reload + BDD)
docker compose --profile dev-full up
```

---

## Comparaison des Modes

| Aspect | Module 4 | Full | Full + Monitoring |
|--------|----------|------|-------------------|
| **Image API** | ~200 MB | ~4 GB | ~4 GB |
| **RAM minimum** | 512 MB | 4 GB | 8 GB |
| **Temps de build** | ~30 sec | ~10 min | ~10 min |
| **Services** | 1 | 6 | 12 |
| **Dépendances** | Aucune | PostgreSQL, Redis, Qdrant | + ELK Stack |
| **Use case** | Ranking livreurs | Recommandations complètes | Production |

---

## Build Manuel des Images

### Image Module 4 (Légère)

```bash
# Build
docker build --target api-module4 -t ar-as-module4:latest .

# Run
docker run -d \
  --name ar-as-module4 \
  -p 8000:8000 \
  -e LOG_LEVEL=INFO \
  ar-as-module4:latest

# Test
curl http://localhost:8000/api/v1/livreur-ranking/health
```

### Image Complète

```bash
# Build
docker build --target api-full -t ar-as-full:latest .

# Les autres images
docker build --target worker -t ar-as-worker:latest .
docker build --target beat -t ar-as-beat:latest .
docker build --target flower -t ar-as-flower:latest .
```

### Image Développement

```bash
# Module 4
docker build --target development -t ar-as-dev:latest .

# Complet
docker build --target development-full -t ar-as-dev-full:latest .
```

---

## Variables d'Environnement

Créer un fichier `.env` à la racine:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
API_PORT=8000

# PostgreSQL (profil full uniquement)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=recommendation_db
POSTGRES_PORT=5432

# Redis (profil full uniquement)
REDIS_PORT=6379

# Qdrant (profil full uniquement)
QDRANT_PORT=6333

# Flower (monitoring Celery)
FLOWER_PORT=5555
FLOWER_USER=admin
FLOWER_PASSWORD=admin

# Monitoring ELK (profil monitoring)
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
APM_PORT=8200
APM_ENABLED=true
```

---

## Endpoints Disponibles

### Module 4 - Livreur Ranking

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/livreur-ranking/rank` | POST | Ranking des livreurs |
| `/api/v1/livreur-ranking/health` | GET | Health check |
| `/docs` | GET | Documentation Swagger |

### Système Complet

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/recommendations/` | POST | Recommandations véhicules |
| `/api/v1/sentiment/analyze` | POST | Analyse de sentiment |
| `/api/v1/livreur-ranking/rank` | POST | Ranking des livreurs |
| `/health` | GET | Health check global |

---

## Exemple de Requête Module 4

```bash
curl -X POST http://localhost:8000/api/v1/livreur-ranking/rank \
  -H "Content-Type: application/json" \
  -d '{
    "annonce": {
      "annonce_id": "A123",
      "point_ramassage": {"latitude": 48.8566, "longitude": 2.3522},
      "point_livraison": {"latitude": 48.8738, "longitude": 2.2950},
      "type_livraison": "express"
    },
    "livreurs_candidats": [
      {
        "livreur_id": "L1",
        "position_actuelle": {"latitude": 48.8600, "longitude": 2.3400},
        "reputation": 4.5,
        "capacite_max_kg": 50,
        "type_vehicule": "moto"
      },
      {
        "livreur_id": "L2",
        "position_actuelle": {"latitude": 48.8700, "longitude": 2.3000},
        "reputation": 4.8,
        "capacite_max_kg": 100,
        "type_vehicule": "voiture"
      }
    ]
  }'
```

---

## Ports Utilisés

| Service | Port | Profil |
|---------|------|--------|
| API | 8000 | Tous |
| PostgreSQL | 5432 | full |
| Redis | 6379 | full |
| Qdrant | 6333 | full |
| Flower | 5555 | full |
| Elasticsearch | 9200 | monitoring |
| Kibana | 5601 | monitoring |
| APM Server | 8200 | monitoring |

---

## Troubleshooting

### Module 4 ne démarre pas

```bash
# Vérifier les logs
docker compose --profile module4 logs api-module4

# Rebuild l'image
docker compose --profile module4 build --no-cache
```

### Problème de mémoire (système complet)

```bash
# Vérifier l'utilisation mémoire
docker stats

# Augmenter les limites Docker Desktop: Settings > Resources > Memory (min 8GB)
```

### Base de données non accessible

```bash
# Vérifier que PostgreSQL est healthy
docker compose --profile full ps postgres

# Voir les logs
docker compose --profile full logs postgres
```

### Reset complet

```bash
# Arrêter et supprimer tout (volumes inclus)
docker compose --profile full --profile monitoring down -v

# Supprimer les images
docker image rm ar-as-api ar-as-module4 ar-as-worker ar-as-beat ar-as-flower
```

---

## Monitoring (Stack ELK)

### Accès aux Dashboards

1. **Kibana**: http://localhost:5601
2. **APM**: http://localhost:5601/app/apm
3. **Elasticsearch**: http://localhost:9200

### Importer les Dashboards

```bash
# Importer les visualisations pré-configurées
curl -X POST "http://localhost:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@monitoring/kibana/dashboards/recommendation-dashboards.ndjson
```

### Alertes Configurées

- **High Error Rate**: >10 erreurs en 5 minutes
- **Slow API Response**: >5 requêtes >2s en 5 minutes
- **Cache Low Hit Rate**: >100 cache misses en 10 minutes

---

## Résumé des Commandes

```bash
# ============= MODULE 4 UNIQUEMENT =============
docker compose --profile module4 up -d          # Démarrer
docker compose --profile module4 down           # Arrêter
docker compose --profile module4 logs -f        # Logs

# ============= SYSTÈME COMPLET =============
docker compose --profile full up -d             # Démarrer
docker compose --profile full down              # Arrêter

# ============= AVEC MONITORING =============
docker compose --profile full --profile monitoring up -d

# ============= DÉVELOPPEMENT =============
docker compose --profile dev up                 # Dev Module 4
docker compose --profile dev-full up            # Dev complet

# ============= MAINTENANCE =============
docker compose --profile full down -v           # Reset avec volumes
docker system prune -a                          # Nettoyage Docker
```
