# 🚀 TRANSFORMATION MULTI-TENANT - RAPPORT COMPLET

## 📋 Résumé Exécutif

Ce document détaille la transformation du système de recommandation mono-domaine (véhicules) en une plateforme **RaaS (Recommendation-as-a-Service)** multi-tenant capable de servir n'importe quel domaine métier.

### Décisions Architecturales Finales

| Composant | Décision | Justification |
|-----------|----------|---------------|
| **Configuration Store** | PostgreSQL | Simple, déjà présent, adapté aux configs structurées |
| **Celery** | ❌ SUPPRIMER | FastAPI async suffit, simplification architecture |
| **Module 4 (Livreur Ranking)** | ✅ GARDER | Module à part, API dédiée, pas d'interférence |
| **Frontend** | Next.js | Moderne, performant, SSR, excellent DX |
| **Auth Server** | Keycloak | À déployer, OAuth2 standard, multi-tenant natif |
| **Données véhicules** | ❌ SUPPRIMER | Restart from scratch |

---

## 🎯 Objectifs de la Transformation

### Vision

Transformer le système actuel en plateforme universelle où:
- **Les plateformes clientes** gèrent leurs propres données produits
- **Notre service** fournit uniquement la recommandation IA
- **Chaque tenant** a son espace isolé (collection Qdrant, configs, quotas)
- **Le scoring** est personnalisable par domaine métier

### Architecture "Bring Your Own Data"

```
┌────────────────────────────────────────────────────────────────┐
│                    PLATEFORMES CLIENTES                         │
│  - Immobilier Pro    - AutoMarket      - FoodieApp             │
│  - Leurs BD propres  - Leurs produits  - Leurs règles          │
└──────────────────────────┬─────────────────────────────────────┘
                           │
              POST descriptions JSON (avec IDs)
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                    NOTRE SERVICE RaaS                           │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Keycloak    │  │   FastAPI    │  │   Qdrant     │        │
│  │  OAuth2      │→ │  Multi-Tenant │→ │  Collections │        │
│  │  Auth        │  │  API         │  │  par Tenant  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  PostgreSQL  │  │   Redis      │  │   Next.js    │        │
│  │  Configs     │  │  Rate Limit  │  │  Admin UI    │        │
│  │  Tenants     │  │  Cache       │  │  Monitoring  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

---

## 📊 Analyse Comparative

### Ce Qui Reste (Réutilisable)

| Composant | État | Modifications |
|-----------|------|---------------|
| **Module 1 - Sentiment** | ✅ GARDER TEL QUEL | Aucune, déjà générique |
| **FastAPI Core** | ✅ GARDER | Refactoriser middleware auth |
| **Redis** | ✅ GARDER | Ajouter gestion quotas par tenant |
| **Qdrant** | ✅ GARDER | Passer à collections multiples |
| **Module 4 - Livreur Ranking** | ✅ GARDER | Isoler, API dédiée séparée |
| **Tests** | ✅ GARDER | Adapter aux nouveaux endpoints |
| **Docker** | ✅ GARDER | Ajouter Keycloak, supprimer ELK |

### Ce Qui Change

| Composant | Avant | Après |
|-----------|-------|-------|
| **PostgreSQL** | Stocke Vehicle (230 cols) | Stocke UNIQUEMENT configs tenants |
| **Qdrant** | Collection unique "vehicles" | Collections par tenant |
| **Authentification** | JWT basique | OAuth2 + Keycloak multi-tenant |
| **Rate Limiting** | Global 100/min | Par tenant, quotas différenciés |
| **Scoring** | Hardcodé véhicules | Configurable via admin UI |
| **Module 2** | Couplé véhicules | Générique multi-tenant |

### Ce Qui Disparaît

| Composant | Raison |
|-----------|--------|
| **Celery + Workers** | Inutile, FastAPI async suffit |
| **Celery Beat** | Inutile, pas de tâches récurrentes critiques |
| **Flower** | Dépendance de Celery |
| **ELK Stack** | Trop complexe, remplacé par UI custom |
| **Elasticsearch** | N/A |
| **Kibana** | N/A |
| **Logstash** | N/A |
| **Filebeat/Metricbeat** | N/A |
| **Modèle Vehicle ORM** | Plus de stockage produits |
| **VehicleRepository** | Plus de data access layer |
| **Migrations Alembic** | Plus de gestion schémas produits |
| **Endpoint véhicules** | Plus mono-domaine |

---

## 🏗️ Architecture Cible

### Stack Technique Finale

```yaml
Backend:
  - FastAPI 0.116+                    # API core
  - Python 3.11+                      # Runtime
  - Uvicorn (4 workers)               # ASGI server
  - Pydantic 2.11+                    # Validation
  - Structlog                         # Logging JSON

Authentification:
  - Keycloak 25.x                     # Auth server
  - python-keycloak 4.5+              # Client Python
  - OAuth2 + OIDC                     # Standards

Stockage:
  - Qdrant 1.7.4                      # Vectors (collections par tenant)
  - PostgreSQL 15+                    # Configs tenants, scoring weights
  - Redis 7.1                         # Cache + Rate limiting

Machine Learning:
  - distil-camembert                  # Sentiment analysis (FR)
  - mpnet-base-v2                     # Embeddings (768D)
  - Transformers 4.55+                # Hugging Face
  - PyTorch 2.9 (CPU)                 # Framework ML

Frontend:
  - Next.js 14+                       # Framework React SSR
  - TypeScript                        # Type safety
  - Tailwind CSS                      # Styling
  - Shadcn/ui                         # Components
  - Recharts                          # Dashboards

Infrastructure:
  - Docker Compose                    # Orchestration
  - Nginx (optionnel)                 # Reverse proxy
```

### Services Docker

```yaml
services:
  # API Backend
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [postgres, redis, qdrant, keycloak]

  # Auth Server
  keycloak:
    image: quay.io/keycloak/keycloak:25.0
    ports: ["8080:8080"]
    environment:
      - KEYCLOAK_ADMIN=admin
      - KC_DB=postgres

  # Databases
  postgres:
    image: postgres:15-alpine
    volumes: [postgres-data:/var/lib/postgresql/data]

  redis:
    image: redis:7.1-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:v1.7.4
    ports: ["6333:6333"]
    volumes: [qdrant-data:/qdrant/storage]

  # Frontend
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]
```

---

## 🔄 Modifications Détaillées

### 1. Base de Données PostgreSQL

#### Avant
```python
# src/database/models.py
class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(UUID, primary_key=True)
    brand = Column(String)
    model = Column(String)
    year = Column(Integer)
    # ... 230 colonnes

    def to_description(self):
        return f"Véhicule {self.brand} {self.model}..."
```

#### Après
```python
# src/database/models.py
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(String, unique=True, index=True)  # Ex: "immopro_123"
    name = Column(String)                                # Ex: "Immobilier Pro"
    domain = Column(String)                              # Ex: "real_estate"
    status = Column(Enum(TenantStatus))                  # active, suspended, deleted

    # OAuth Config
    keycloak_client_id = Column(String)
    keycloak_realm = Column(String, default="raas")

    # Rate Limiting
    rate_limit_per_minute = Column(Integer, default=100)
    rate_limit_burst = Column(Integer, default=20)

    # Qdrant
    qdrant_collection_name = Column(String)              # Ex: "tenant_immopro_123"

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ScoringConfig(Base):
    __tablename__ = "scoring_configs"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"))

    # Critères de scoring COMPLÈTEMENT dynamiques (JSON)
    scoring_criteria = Column(JSON)  # Liste de critères configurables
    # Format:
    # [
    #   {
    #     "name": "similarity",
    #     "weight": 0.70,
    #     "type": "system",  // Toujours présent
    #     "description": "Similarité sémantique"
    #   },
    #   {
    #     "name": "price_match",
    #     "weight": 0.15,
    #     "type": "custom",
    #     "metadata_key": "price",
    #     "normalization": "inverse",  // inverse, direct, custom
    #     "description": "Correspondance de prix"
    #   },
    #   // ... autres critères ajoutables/supprimables
    # ]

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relations
    tenant = relationship("Tenant", back_populates="scoring_config")


class ScoringCriterion(BaseModel):
    """Pydantic model pour validation des critères."""
    name: str
    weight: float  # 0.0 à 1.0
    type: Literal["system", "custom"]
    metadata_key: Optional[str] = None  # Pour type=custom
    normalization: Optional[Literal["direct", "inverse", "custom"]] = "direct"
    description: Optional[str] = None
```

**Actions:**
- ❌ Supprimer `Vehicle`, `Personne` models
- ✅ Créer `Tenant`, `ScoringConfig` models
- ✅ Créer migrations Alembic pour nouveaux schémas
- ✅ Script de cleanup des anciennes tables

---

### 2. Module 2 - Recommendation Engine

#### Avant (Couplé Véhicules)
```python
# src/modules/module2_recommendation/engine.py
class RecommendationEngine:
    def __init__(self, db, cache, vector_store, embedding_service):
        self.db = db
        self.repo = VehicleRepository(db)
        # ...

    async def recommend(self, product_id: UUID, comment: str, top_k: int):
        # 1. Récupère véhicule depuis DB
        vehicle = await self.repo.get_by_id(product_id)
        if not vehicle:
            raise NotFoundError()

        # 2. Génère description hardcodée véhicules
        description = vehicle.to_description()

        # 3. Embedding
        embedding = await self.embedding_service.generate(comment)

        # 4. Search Qdrant collection unique
        results = await self.vector_store.search(
            collection_name="vehicles",
            query_vector=embedding,
            limit=100
        )

        # 5. Scoring hardcodé
        scores = self.ranking.calculate(
            results,
            similarity_weight=0.6,
            availability_weight=0.25,
            reputation_weight=0.15
        )

        return scores[:top_k]
```

#### Après (Multi-Tenant Générique)
```python
# src/modules/module2_recommendation/engine.py
class MultiTenantRecommendationEngine:
    def __init__(self, cache, vector_store, embedding_service, config_service):
        # Plus de DB de produits!
        self.cache = cache
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config_service = config_service

    async def recommend(
        self,
        tenant_id: str,
        user_query: str,
        top_k: int = 10,
        filters: Optional[dict] = None
    ) -> List[RecommendationResult]:
        """
        Recommandation générique multi-tenant.

        Args:
            tenant_id: ID du tenant (ex: "immopro_123")
            user_query: Requête utilisateur (ex: "Appartement Paris proche métro")
            top_k: Nombre de résultats
            filters: Filtres optionnels sur metadata (ex: {"price_max": 500000})

        Returns:
            Liste d'IDs de produits + scores
        """
        # 1. Vérifier cache
        cache_key = f"rec:{tenant_id}:{hash(user_query)}:{top_k}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # 2. Récupérer config scoring du tenant
        scoring_config = await self.config_service.get_scoring_config(tenant_id)

        # 3. Embedding de la requête utilisateur
        query_embedding = await self.embedding_service.generate(user_query)

        # 4. Recherche vectorielle dans la collection du tenant
        collection_name = f"tenant_{tenant_id}"

        search_results = await self.vector_store.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=100,  # Sur-échantillonner pour re-ranking
            filters=filters  # Filtres sur metadata (prix, catégorie, etc.)
        )

        # 5. Re-ranking avec scoring personnalisé
        ranked_results = await self._calculate_final_scores(
            search_results,
            scoring_config
        )

        # 6. Top-K résultats
        top_results = ranked_results[:top_k]

        # 7. Format de sortie (juste IDs + scores, pas de données produit)
        output = [
            RecommendationResult(
                product_id=r.payload["id"],  # ID dans la DB de la plateforme
                score=r.final_score,
                similarity=r.similarity_score,
                metadata=r.payload.get("metadata", {})
            )
            for r in top_results
        ]

        # 8. Cache
        await self.cache.set(cache_key, output, ttl=3600)

        return output

    async def _calculate_final_scores(
        self,
        results: List[QdrantSearchResult],
        config: ScoringConfig
    ) -> List[ScoredResult]:
        """
        Calcule scores finaux avec poids personnalisés.

        Formule:
        Score = w1*Similarity + w2*Price + w3*Availability + w4*Reputation + ...
        """
        scored = []

        for result in results:
            # Similarité vectorielle (0-1)
            similarity = result.score

            # Critères depuis metadata (normalisés 0-1)
            metadata = result.payload.get("metadata", {})

            # Calcul score final selon config tenant
            final_score = (
                config.similarity_weight * similarity +
                config.price_weight * self._normalize_price(metadata.get("price")) +
                config.availability_weight * metadata.get("availability", 1.0) +
                config.reputation_weight * metadata.get("reputation", 0.5)
            )

            # Critères custom (optionnel)
            for custom_key, custom_weight in config.custom_criteria.items():
                if custom_key in metadata:
                    final_score += custom_weight * metadata[custom_key]

            scored.append(
                ScoredResult(
                    payload=result.payload,
                    similarity_score=similarity,
                    final_score=final_score
                )
            )

        # Tri décroissant
        return sorted(scored, key=lambda x: x.final_score, reverse=True)
```

**Actions:**
- ✅ Supprimer dépendance `VehicleRepository`
- ✅ Ajouter paramètre `tenant_id` partout
- ✅ Récupérer config scoring depuis `ScoringConfig` DB
- ✅ Recherche dans collection dynamique `tenant_{tenant_id}`
- ✅ Scoring flexible basé sur config
- ✅ Retourner uniquement IDs + scores (pas les données produits)

---

### 3. API Routes - Nouveaux Endpoints

#### Endpoints à Créer

```python
# src/api/routes/tenants.py

@router.post("/tenants/{tenant_id}/products", status_code=201)
async def add_products(
    tenant_id: str,
    products: List[ProductDescription],
    current_tenant: Tenant = Depends(verify_tenant_access)
):
    """
    Endpoint pour que les plateformes ajoutent/mettent à jour leurs produits.

    Body:
    {
      "products": [
        {
          "id": "prod_abc123",  # ID dans la DB de la plateforme
          "description": "Appartement 3 pièces Paris 15e, proche métro...",
          "metadata": {
            "price": 250000,
            "surface": 65,
            "rooms": 3,
            "location": "Paris 15e"
          }
        },
        ...
      ]
    }

    Process:
    1. Vérifie authentification OAuth (tenant autorisé)
    2. Génère embeddings pour chaque description
    3. Stocke dans Qdrant collection tenant_{tenant_id}
    4. Retourne statut
    """
    pass


@router.post("/tenants/{tenant_id}/recommendations")
async def get_recommendations(
    tenant_id: str,
    request: RecommendationRequest,
    current_tenant: Tenant = Depends(verify_tenant_access)
):
    """
    Endpoint de recommandation.

    Body:
    {
      "query": "Je cherche un appartement lumineux avec balcon",
      "top_k": 10,
      "filters": {
        "price_max": 300000,
        "rooms_min": 2
      }
    }

    Response:
    {
      "recommendations": [
        {
          "product_id": "prod_abc123",
          "score": 0.87,
          "similarity": 0.92,
          "metadata": {...}
        },
        ...
      ],
      "processing_time_ms": 45
    }
    """
    pass


@router.delete("/tenants/{tenant_id}/products/{product_id}")
async def delete_product(
    tenant_id: str,
    product_id: str,
    current_tenant: Tenant = Depends(verify_tenant_access)
):
    """
    Supprime un produit de la collection Qdrant.
    """
    pass


@router.get("/tenants/{tenant_id}/products/count")
async def get_products_count(
    tenant_id: str,
    current_tenant: Tenant = Depends(verify_tenant_access)
):
    """
    Compte le nombre de produits dans la collection.
    """
    pass
```

```python
# src/api/routes/admin.py

@router.post("/admin/tenants", status_code=201)
async def create_tenant(
    tenant: TenantCreate,
    current_user: User = Depends(verify_admin)
):
    """
    Crée un nouveau tenant (admin uniquement).

    Actions:
    1. Crée entrée dans PostgreSQL
    2. Crée collection Qdrant
    3. Crée client Keycloak
    4. Retourne credentials OAuth
    """
    pass


@router.put("/admin/tenants/{tenant_id}/scoring")
async def update_scoring_config(
    tenant_id: str,
    config: ScoringConfigUpdate,
    current_user: User = Depends(verify_admin)
):
    """
    Met à jour la config de scoring d'un tenant.
    """
    pass


@router.get("/admin/metrics")
async def get_global_metrics(
    current_user: User = Depends(verify_admin)
):
    """
    Métriques globales (tous tenants).
    """
    pass
```

**Actions:**
- ✅ Créer `tenants.py` avec endpoints produits
- ✅ Créer `admin.py` avec gestion tenants
- ❌ Supprimer anciens endpoints véhicules
- ✅ Migrer `health.py`, `sentiment.py` (pas de changement)

---

### 4. Authentification OAuth2 + Keycloak

#### Configuration Keycloak

```yaml
# Realm: raas
Clients:
  - client_id: "immopro_client"
    client_secret: "xxx"
    redirect_uris: ["https://immopro.com/callback"]
    standard_flow_enabled: true
    service_accounts_enabled: true  # Pour machine-to-machine

  - client_id: "automarket_client"
    client_secret: "yyy"
    ...

Roles:
  - tenant_user    # Accès API tenant
  - admin          # Accès admin interface

Token Claims:
  - tenant_id      # Custom claim pour identifier le tenant
  - permissions    # Permissions granulaires
```

#### Middleware Auth

```python
# src/api/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from keycloak import KeycloakOpenID

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

keycloak_openid = KeycloakOpenID(
    server_url="http://keycloak:8080/",
    realm_name="raas",
    client_id="api-gateway",
    client_secret_key="xxx"
)


async def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Vérifie le token JWT Keycloak.

    Returns:
        Decoded token with claims (tenant_id, sub, roles, etc.)
    """
    try:
        # Introspect token
        token_info = keycloak_openid.introspect(token)

        if not token_info.get("active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired or invalid"
            )

        return token_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


async def get_current_tenant(token_info: dict = Depends(verify_token)) -> Tenant:
    """
    Extrait le tenant depuis le token.
    """
    tenant_id = token_info.get("tenant_id")

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant_id in token"
        )

    # Récupère tenant depuis DB
    tenant = await tenant_service.get_by_id(tenant_id)

    if not tenant or tenant.status != TenantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found or inactive"
        )

    return tenant


async def verify_tenant_access(
    tenant_id: str,
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """
    Vérifie que le tenant du token correspond au tenant de la requête.
    """
    if current_tenant.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    return current_tenant
```

**Actions:**
- ✅ Déployer Keycloak dans Docker Compose
- ✅ Créer realm `raas`
- ✅ Créer middleware `verify_token`, `get_current_tenant`
- ✅ Ajouter dépendances: `python-keycloak`, `python-jose[cryptography]`
- ✅ Configurer CORS pour tokens

---

### 5. Rate Limiting par Tenant

#### Middleware Redis

```python
# src/api/middleware/rate_limit.py
import time
from fastapi import Request, HTTPException, status
from redis.asyncio import Redis

class TenantRateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_rate_limit(
        self,
        tenant_id: str,
        limit_per_minute: int,
        burst: int
    ):
        """
        Rate limiting Token Bucket par tenant.

        Args:
            tenant_id: ID du tenant
            limit_per_minute: Limite requêtes/minute
            burst: Rafale autorisée
        """
        now = time.time()
        window = 60  # 1 minute

        # Clés Redis
        key = f"rate_limit:{tenant_id}:minute"

        # Incrémente compteur
        async with self.redis.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()

        current_count = results[0]

        # Vérifie limite
        if current_count > limit_per_minute + burst:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit_per_minute} req/min",
                headers={
                    "X-RateLimit-Limit": str(limit_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now) + window)
                }
            )

        return {
            "limit": limit_per_minute,
            "remaining": max(0, limit_per_minute - current_count),
            "reset": int(now) + window
        }


# Middleware FastAPI
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip pour routes publiques (health, docs)
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)

    # Extrait tenant depuis token (injecté par auth middleware)
    tenant = getattr(request.state, "tenant", None)

    if tenant:
        rate_limiter = TenantRateLimiter(redis_client)

        rate_info = await rate_limiter.check_rate_limit(
            tenant_id=tenant.tenant_id,
            limit_per_minute=tenant.rate_limit_per_minute,
            burst=tenant.rate_limit_burst
        )

        # Ajoute headers de rate limit
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response

    return await call_next(request)
```

**Actions:**
- ✅ Créer `TenantRateLimiter` avec algorithme Token Bucket
- ✅ Ajouter middleware FastAPI
- ✅ Stocker quotas dans table `Tenant`
- ✅ Headers standards `X-RateLimit-*`

---

### 6. Frontend Next.js

#### Structure

```
frontend/
├── app/
│   ├── layout.tsx                  # Root layout
│   ├── page.tsx                    # Landing page
│   ├── dashboard/
│   │   ├── page.tsx               # Dashboard principal
│   │   ├── tenants/
│   │   │   ├── page.tsx           # Liste tenants
│   │   │   ├── [id]/
│   │   │   │   ├── page.tsx       # Détail tenant
│   │   │   │   ├── products/
│   │   │   │   │   └── page.tsx   # Gestion produits
│   │   │   │   ├── scoring/
│   │   │   │   │   └── page.tsx   # Config scoring
│   │   │   │   └── metrics/
│   │   │   │       └── page.tsx   # Métriques tenant
│   │   │   └── new/
│   │   │       └── page.tsx       # Créer tenant
│   │   └── monitoring/
│   │       └── page.tsx            # Monitoring global
│   └── api/
│       └── auth/
│           └── [...nextauth]/
│               └── route.ts        # NextAuth.js Keycloak
│
├── components/
│   ├── ui/                         # Shadcn/ui components
│   ├── dashboard/
│   │   ├── TenantCard.tsx
│   │   ├── MetricsChart.tsx
│   │   ├── ScoringConfigForm.tsx
│   │   └── ProductUploader.tsx
│   └── layout/
│       ├── Navbar.tsx
│       └── Sidebar.tsx
│
├── lib/
│   ├── api.ts                      # API client
│   ├── auth.ts                     # Auth config
│   └── utils.ts
│
├── types/
│   ├── tenant.ts
│   ├── scoring.ts
│   └── metrics.ts
│
├── public/
├── package.json
├── tsconfig.json
└── tailwind.config.ts
```

#### Fonctionnalités Clés

**Dashboard Principal:**
- Vue d'ensemble tous tenants
- Graphiques métriques (requêtes/min, latence, cache hit rate)
- Alertes (quotas dépassés, erreurs)

**Gestion Tenants:**
- CRUD tenants
- Configuration OAuth (client_id, realm)
- Quotas rate limiting
- Statut (active, suspended)

**Configuration Scoring (COMPLÈTEMENT DYNAMIQUE):**
- **Ajouter un critère** : Bouton "+" pour créer nouveau critère custom
  - Nom du critère
  - Clé metadata (ex: "price", "availability")
  - Type de normalisation (direct, inverse, custom)
  - Poids (slider 0-100%)
- **Supprimer un critère** : Bouton "×" sur chaque critère (sauf "similarity")
- **Modifier les poids** : Sliders interactifs avec ajustement auto pour maintenir total = 100%
- **Preview en temps réel** : Graphique montrant la pondération
- **Validation** : Somme des poids = 1.0 (100%)
- **Critère "similarity" obligatoire** : Ne peut pas être supprimé, toujours présent

**Monitoring:**
- Métriques temps réel (WebSocket ou polling)
- Logs structurés
- Latence P50/P95/P99
- Taux d'erreur

**Stack:**
```json
{
  "dependencies": {
    "next": "14.2.0",
    "react": "18.3.0",
    "next-auth": "^5.0.0",
    "@tanstack/react-query": "^5.0.0",
    "recharts": "^2.12.0",
    "zod": "^3.23.0",
    "tailwindcss": "^3.4.0",
    "@radix-ui/react-*": "latest",
    "lucide-react": "^0.400.0"
  }
}
```

**Actions:**
- ✅ Init projet Next.js 14 avec App Router
- ✅ Intégrer Shadcn/ui pour composants
- ✅ Config NextAuth.js avec Keycloak provider
- ✅ Créer layouts Dashboard
- ✅ Créer pages CRUD tenants
- ✅ Créer interface config scoring (sliders)
- ✅ Créer dashboards monitoring (Recharts)
- ✅ API routes pour proxy backend

---

### 7. Module 4 - Livreur Ranking (Isolé)

**Décision:** GARDER mais isoler complètement.

```python
# src/modules/module4_livreur_ranking/
# → Reste identique, aucune modification

# src/api/routes/livreur_ranking.py
# → Reste identique, routes dédiées séparées

# Tests
# tests/modules/module4_livreur_ranking/
# → Reste identique
```

**Justification:**
- Module stateless, pas d'interférence avec multi-tenant
- Performance excellente (23ms)
- Cas d'usage spécifique qui peut rester en parallèle
- API dédiée `/api/v1/livreurs/rank`

**Actions:**
- ✅ Aucune modification nécessaire
- ✅ Garder routes séparées
- ✅ Documentation indépendante

---

## 🗑️ Éléments à Supprimer

### Fichiers et Répertoires

```bash
# Celery & Workers
src/modules/module3_orchestration/
src/api/routes/tasks.py

# ELK Stack
monitoring/
docker-compose.yml (services ELK)

# Modèles Vehicle
src/database/models.py (classe Vehicle, Personne)
src/database/repositories.py (VehicleRepository)
src/database/migrations/ (migrations véhicules)

# Scripts spécifiques
scripts/init_vectors.py (hardcodé véhicules)
```

### Dépendances Python

```txt
# À retirer de requirements.txt
celery==5.6.2
flower==2.0.1
kombu==5.4.2
vine==5.1.0

elastic-apm==6.20.0
elasticsearch==8.x
```

### Services Docker

```yaml
# À retirer de docker-compose.yml
services:
  celery-worker: ❌
  celery-beat: ❌
  flower: ❌
  elasticsearch: ❌
  kibana: ❌
  logstash: ❌
  filebeat: ❌
  metricbeat: ❌
```

### Configuration

```python
# src/config/settings.py
# À retirer:
celery_broker_url
celery_result_backend
celery_worker_concurrency
celery_task_routes

apm_enabled
apm_server_url
apm_service_name

elastic_host
elastic_port
kibana_host
```

---

## 📝 Checklist Complète

### Phase 0: Préparation
- [ ] Backup complet de la DB actuelle
- [ ] Documenter flux existants
- [ ] Créer branche `feature/multi-tenant`
- [ ] Setup environnement dev avec Keycloak local

### Phase 1: Nettoyage (1 semaine)
- [ ] Supprimer Celery
  - [ ] Retirer services Docker (worker, beat, flower)
  - [ ] Supprimer `module3_orchestration/`
  - [ ] Supprimer dépendances requirements.txt
  - [ ] Adapter endpoints async (supprimer `/async`)

- [ ] Supprimer ELK
  - [ ] Retirer services Docker (ES, Kibana, Logstash, beats)
  - [ ] Supprimer `monitoring/`
  - [ ] Retirer `elastic-apm`
  - [ ] Simplifier logging (garder structlog JSON)

- [ ] Nettoyer DB
  - [ ] Script pour DROP tables véhicules
  - [ ] Supprimer migrations Alembic véhicules
  - [ ] Supprimer modèles `Vehicle`, `Personne`
  - [ ] Supprimer `VehicleRepository`

### Phase 2: Nouveaux Modèles (1 semaine)
- [ ] Créer modèles PostgreSQL
  - [ ] `Tenant` (tenant_id, name, domain, oauth config)
  - [ ] `ScoringConfig` (weights, custom_criteria)
  - [ ] Migrations Alembic

- [ ] Créer services
  - [ ] `TenantService` (CRUD tenants)
  - [ ] `ScoringConfigService` (gestion configs)
  - [ ] Tests unitaires

### Phase 3: Authentification OAuth2 (1 semaine)
- [ ] Setup Keycloak
  - [ ] Docker Compose service
  - [ ] Init realm `raas`
  - [ ] Config clients par défaut
  - [ ] Roles et permissions

- [ ] Middleware Auth
  - [ ] `verify_token()`
  - [ ] `get_current_tenant()`
  - [ ] `verify_tenant_access()`
  - [ ] Tests intégration

- [ ] Rate Limiting
  - [ ] `TenantRateLimiter` Redis
  - [ ] Middleware FastAPI
  - [ ] Headers `X-RateLimit-*`

### Phase 4: Refactoriser Module 2 (2 semaines)
- [ ] `MultiTenantRecommendationEngine`
  - [ ] Supprimer dépendance `VehicleRepository`
  - [ ] Paramètre `tenant_id` partout
  - [ ] Collections dynamiques Qdrant
  - [ ] Scoring flexible depuis `ScoringConfig`
  - [ ] Tests unitaires complets

- [ ] `VectorStoreService`
  - [ ] Support collections multiples
  - [ ] CRUD collections
  - [ ] Filtres sur metadata

- [ ] `CacheService`
  - [ ] Clés par tenant
  - [ ] TTL configurable

### Phase 5: Nouveaux Endpoints API (1 semaine)
- [ ] Routes Tenants (`/tenants/{id}/`)
  - [ ] `POST /products` (ajouter produits)
  - [ ] `POST /recommendations` (obtenir reco)
  - [ ] `DELETE /products/{product_id}`
  - [ ] `GET /products/count`

- [ ] Routes Admin (`/admin/`)
  - [ ] `POST /tenants` (créer tenant)
  - [ ] `PUT /tenants/{id}/scoring` (config scoring)
  - [ ] `GET /metrics` (métriques globales)

- [ ] Tests API (Pytest + TestClient)

### Phase 6: Frontend Next.js (2 semaines)
- [ ] Setup projet
  - [ ] Init Next.js 14 + TypeScript
  - [ ] Shadcn/ui installation
  - [ ] Tailwind config
  - [ ] NextAuth.js Keycloak

- [ ] Pages Dashboard
  - [ ] Landing page
  - [ ] Dashboard principal (overview)
  - [ ] Liste tenants
  - [ ] Détail tenant
  - [ ] Config scoring (sliders)
  - [ ] Monitoring (Recharts)

- [ ] Composants
  - [ ] `TenantCard`
  - [ ] `MetricsChart`
  - [ ] `ScoringConfigForm`
  - [ ] `ProductUploader`

- [ ] API Client
  - [ ] Axios/Fetch wrapper
  - [ ] React Query hooks
  - [ ] Error handling

### Phase 7: Tests & Documentation (1 semaine)
- [ ] Tests E2E
  - [ ] Playwright setup
  - [ ] User flows (create tenant, config scoring, reco)

- [ ] Documentation
  - [ ] OpenAPI/Swagger à jour
  - [ ] Guide d'intégration pour plateformes
  - [ ] Exemples code (curl, Python, Node.js)
  - [ ] README.md mis à jour

- [ ] Migration guide
  - [ ] Changelog détaillé
  - [ ] Breaking changes

### Phase 8: Déploiement (1 semaine)
- [ ] Docker
  - [ ] Multi-stage build optimisé
  - [ ] Docker Compose prod
  - [ ] Healthchecks
  - [ ] Volumes persistence

- [ ] CI/CD
  - [ ] GitHub Actions / GitLab CI
  - [ ] Tests auto
  - [ ] Deploy staging
  - [ ] Deploy prod

- [ ] Monitoring Prod
  - [ ] Métriques (Prometheus optionnel)
  - [ ] Logs centralisés (interface custom)
  - [ ] Alerting

---

## ⏱️ Timeline Estimée

| Phase | Durée | Dépendances |
|-------|-------|-------------|
| **Phase 0: Préparation** | 2-3 jours | Aucune |
| **Phase 1: Nettoyage** | 1 semaine | Phase 0 |
| **Phase 2: Modèles DB** | 1 semaine | Phase 1 |
| **Phase 3: OAuth2** | 1 semaine | Phase 2 |
| **Phase 4: Module 2** | 2 semaines | Phase 2, 3 |
| **Phase 5: API Routes** | 1 semaine | Phase 4 |
| **Phase 6: Frontend** | 2 semaines | Phase 5 |
| **Phase 7: Tests/Docs** | 1 semaine | Phase 6 |
| **Phase 8: Déploiement** | 1 semaine | Phase 7 |

**TOTAL: ~10 semaines (2.5 mois)**

---

## 🎯 Critères de Succès

### Fonctionnels
- ✅ Plateforme peut créer tenant via interface admin
- ✅ Tenant peut s'authentifier OAuth2 via Keycloak
- ✅ Tenant peut uploader 1000+ produits (descriptions JSON)
- ✅ Tenant peut obtenir recommandations en <50ms (cache hit)
- ✅ Tenant peut configurer scoring via UI (sliders)
- ✅ Isolation complète entre tenants (collections, quotas, cache)

### Techniques
- ✅ 0 dépendance au domaine "véhicules"
- ✅ Tests coverage ≥ 85%
- ✅ Performance: P95 latency <200ms (cache miss)
- ✅ Scalabilité: Support 10+ tenants simultanés
- ✅ Sécurité: OAuth2 + HTTPS + Rate limiting

### Opérationnels
- ✅ Documentation complète (API, intégration, admin)
- ✅ Interface web responsive (desktop + mobile)
- ✅ Monitoring temps réel (métriques par tenant)
- ✅ Logs structurés JSON
- ✅ Docker Compose one-command deploy

---

## 📚 Ressources

### Documentation Technique
- FastAPI: https://fastapi.tiangolo.com/
- Keycloak: https://www.keycloak.org/docs/latest/
- Qdrant: https://qdrant.tech/documentation/
- Next.js: https://nextjs.org/docs
- Shadcn/ui: https://ui.shadcn.com/

### Repos Référence
- OAuth2 multi-tenant: https://github.com/tiangolo/fastapi/discussions/12345
- Keycloak Python: https://github.com/marcospereirampj/python-keycloak
- Next.js Dashboard: https://github.com/vercel/nextjs-dashboard

---

## 🚨 Risques Identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **Complexité OAuth2** | Élevé | POC Keycloak avant intégration complète |
| **Performance Qdrant collections multiples** | Moyen | Benchmarks dès Phase 4 |
| **Gestion quotas Redis** | Moyen | Algorithme Token Bucket éprouvé |
| **Learning curve Next.js** | Faible | Équipe front expérimentée ou templates |
| **Migration breaking changes** | Élevé | Versioning API (v2), période transition |

---

## ✅ Validation

- [ ] Ce document a été relu et approuvé par l'équipe
- [ ] Architecture validée par tech lead
- [ ] Timeline approuvée par PM
- [ ] Budget estimé validé

---

**Date de création:** 2025-01-15
**Dernière mise à jour:** 2025-01-15
**Version:** 1.0
**Auteurs:** Équipe AR_AS
