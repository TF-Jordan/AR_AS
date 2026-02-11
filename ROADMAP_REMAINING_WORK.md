# 🎯 Ce qui Manque pour un Système Multi-Tenant Fonctionnel

## ✅ État Actuel (Phase 0 - TERMINÉE)

```
✓ Audit complet (23 fichiers couplés identifiés)
✓ Keycloak configuré et opérationnel
✓ Scripts de nettoyage créés
✓ Documentation complète
✓ Branch Git prête
```

---

## 🚧 Travail Restant - Vue d'Ensemble

### Résumé Rapide
| Phase | Durée | Statut | Priorité |
|-------|-------|--------|----------|
| **Exécution Cleanup** | 30 min | ⏳ À FAIRE | 🔴 P0 |
| **Phase 1: Nettoyage Code** | 1 semaine | ⏳ À FAIRE | 🔴 P0 |
| **Phase 2: Modèles DB** | 1 semaine | ⏳ À FAIRE | 🔴 P0 |
| **Phase 3: OAuth2 Integration** | 1 semaine | ⏳ À FAIRE | 🔴 P0 |
| **Phase 4: Module 2 Multi-Tenant** | 2 semaines | ⏳ À FAIRE | 🔴 P0 |
| **Phase 5: API Routes** | 1 semaine | ⏳ À FAIRE | 🟡 P1 |
| **Phase 6: Frontend Admin** | 2 semaines | ⏳ À FAIRE | 🟡 P1 |
| **Phase 7: Tests & QA** | 1 semaine | ⏳ À FAIRE | 🟡 P1 |

**Total Estimé:** ~10 semaines (2,5 mois)

---

## 📋 Détail par Phase

### 🔴 ÉTAPE 0: Exécution du Cleanup (30 minutes)

**Objectif:** Supprimer définitivement toutes les données véhicules

#### Actions Requises:
```bash
# 1. Supprimer collection Qdrant
python scripts/cleanup_qdrant_vehicles.py

# 2. Supprimer tables PostgreSQL
docker compose exec postgres psql -U postgres -d ar_as_db -f /scripts/cleanup_vehicle_data.sql
```

#### Résultat Attendu:
- ✅ Collection Qdrant "vehicles" supprimée
- ✅ 17 tables PostgreSQL véhicules supprimées
- ✅ Base de données propre, prête pour nouveau schéma

---

### 🔴 PHASE 1: Nettoyage du Code (1 semaine)

**Objectif:** Retirer tous les composants obsolètes (Celery, ELK, modèles véhicules)

#### 1.1 Supprimer Celery (2 jours)

**Fichiers à Modifier:**
```yaml
docker-compose.yml
├── Supprimer service: celery-worker
├── Supprimer service: celery-beat
└── Supprimer service: flower
```

```
src/
├── modules/module3_orchestration/  ❌ SUPPRIMER ENTIÈREMENT
requirements.txt
├── celery==5.3.4              ❌ SUPPRIMER
├── flower==2.0.1              ❌ SUPPRIMER
└── redis (garder)             ✅ GARDER
```

**Endpoints API à adapter:**
- `POST /api/v1/recommendations/async` → Supprimer (redondant avec `/recommendations`)
- Tous les appels `task.delay()` → Remplacer par `async/await`

#### 1.2 Supprimer ELK Stack (1 jour)

**Fichiers à Modifier:**
```yaml
docker-compose.yml
├── Supprimer service: elasticsearch
├── Supprimer service: kibana
├── Supprimer service: logstash
├── Supprimer service: filebeat
├── Supprimer service: metricbeat
├── Supprimer service: apm-server
└── Supprimer service: es-setup
```

```
monitoring/               ❌ SUPPRIMER DOSSIER ENTIER
requirements.txt
└── elastic-apm==6.18.0   ❌ SUPPRIMER
```

**Garder:** `structlog` pour logging JSON

#### 1.3 Supprimer Modèles Véhicules (2 jours)

**Fichiers à Modifier/Supprimer:**

| Fichier | Action | Lignes Affectées |
|---------|--------|------------------|
| `src/database/models.py` | Supprimer classe `Vehicle` | ~145 lignes |
| `src/database/repositories.py` | Supprimer `VehicleRepository` | ~76 lignes |
| `src/modules/module2_recommendation/engine.py` | Refactoriser (enlever dépendance Vehicle) | ~200 lignes |
| `src/modules/module2_recommendation/vector_store.py` | Refactoriser (collection dynamique) | ~50 lignes |
| `scripts/init_db.sql` | Archiver (garder pour référence) | - |
| `scripts/init_vectors.py` | Supprimer | ~150 lignes |

**Total:** ~621 lignes à supprimer/modifier

---

### 🔴 PHASE 2: Nouveaux Modèles Multi-Tenant (1 semaine)

**Objectif:** Créer le nouveau schéma PostgreSQL pour multi-tenant

#### 2.1 Créer Modèles SQLAlchemy (3 jours)

**Nouveau fichier:** `src/database/models_multitenant.py`

```python
# Modèle 1: Tenant
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    domain = Column(String(100))  # Ex: "real-estate", "automotive"

    # OAuth2 Config
    keycloak_client_id = Column(String(100))

    # Qdrant Collection
    qdrant_collection_name = Column(String(100))  # Ex: "tenant_abc123"

    # Rate Limiting
    rate_limit_requests = Column(Integer, default=100)
    rate_limit_window_seconds = Column(Integer, default=60)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

# Modèle 2: ScoringConfig (CRITIQUE - Dynamique)
class ScoringConfig(Base):
    __tablename__ = "scoring_configs"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"))

    # Configuration Dynamique (JSON)
    scoring_criteria = Column(JSON, nullable=False)
    # Format:
    # [
    #   {"name": "similarity", "weight": 0.70, "type": "system"},
    #   {"name": "price_match", "weight": 0.20, "type": "custom"},
    #   {"name": "location_proximity", "weight": 0.10, "type": "custom"}
    # ]

    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Modèle 3: Product (Optionnel - Stockage des descriptions pour cache)
class ProductDescription(Base):
    __tablename__ = "product_descriptions"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"))
    product_id = Column(String, nullable=False)  # ID externe du client
    description = Column(Text, nullable=False)

    # Cache du vecteur (optionnel)
    vector_embedding = Column(ARRAY(Float), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'product_id', name='uq_tenant_product'),
    )
```

#### 2.2 Créer Migrations Alembic (1 jour)

```bash
# Créer migration
alembic revision --autogenerate -m "Create multi-tenant schema"

# Appliquer migration
alembic upgrade head
```

#### 2.3 Créer Services (2 jours)

**Nouveau fichier:** `src/services/tenant_service.py`

```python
class TenantService:
    async def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        """Créer un nouveau tenant + collection Qdrant"""

    async def get_tenant(self, tenant_id: str) -> Tenant:
        """Récupérer tenant par ID"""

    async def update_tenant(self, tenant_id: str, updates: TenantUpdate) -> Tenant:
        """Mettre à jour tenant"""

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Supprimer tenant + collection Qdrant"""
```

**Nouveau fichier:** `src/services/scoring_service.py`

```python
class ScoringConfigService:
    async def create_config(self, tenant_id: str, criteria: List[ScoringCriterion]) -> ScoringConfig:
        """Créer configuration de scoring"""

    async def get_active_config(self, tenant_id: str) -> ScoringConfig:
        """Récupérer config active"""

    async def update_config(self, tenant_id: str, criteria: List[ScoringCriterion]) -> ScoringConfig:
        """Mettre à jour config (crée nouvelle version)"""
```

---

### 🔴 PHASE 3: Intégration OAuth2 Keycloak (1 semaine)

**Objectif:** Sécuriser l'API avec OAuth2 et extraction du tenant_id

#### 3.1 Middleware d'Authentification (3 jours)

**Nouveau fichier:** `src/auth/keycloak_middleware.py`

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

security = HTTPBearer()

class KeycloakAuth:
    def __init__(self):
        self.keycloak_url = settings.KEYCLOAK_HOST
        self.realm = settings.KEYCLOAK_REALM
        self.jwks_client = PyJWKClient(
            f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        )

    async def verify_token(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> dict:
        """Vérifier token JWT et extraire claims"""
        try:
            token = credentials.credentials
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="raas-api",
                options={"verify_exp": True}
            )

            return payload
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def get_current_tenant(
        self,
        token_payload: dict = Depends(verify_token)
    ) -> str:
        """Extraire tenant_id du token"""
        tenant_id = token_payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=403, detail="No tenant_id in token")
        return tenant_id

# Dependency pour routes protégées
get_current_tenant = KeycloakAuth().get_current_tenant
```

#### 3.2 Rate Limiting par Tenant (2 jours)

**Nouveau fichier:** `src/middleware/rate_limiter.py`

```python
from fastapi import Request, HTTPException
import redis.asyncio as redis
from datetime import datetime

class TenantRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        tenant_id: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> bool:
        """Token Bucket Algorithm"""
        key = f"rate_limit:{tenant_id}"

        # Incrémenter compteur
        count = await self.redis.incr(key)

        if count == 1:
            # Premier appel, définir TTL
            await self.redis.expire(key, window_seconds)

        if count > max_requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(window_seconds)
                }
            )

        return True

# Middleware FastAPI
async def rate_limit_middleware(request: Request, call_next):
    tenant_id = request.state.tenant_id  # Extrait par auth middleware
    tenant = await tenant_service.get_tenant(tenant_id)

    await rate_limiter.check_rate_limit(
        tenant_id,
        tenant.rate_limit_requests,
        tenant.rate_limit_window_seconds
    )

    response = await call_next(request)
    return response
```

#### 3.3 Tests OAuth2 (1 jour)

---

### 🔴 PHASE 4: Refactoriser Module 2 Multi-Tenant (2 semaines)

**Objectif:** Rendre le moteur de recommandation générique et multi-tenant

#### 4.1 Refactoriser RecommendationEngine (1 semaine)

**Fichier:** `src/modules/module2_recommendation/engine.py`

**Changements Principaux:**

```python
# AVANT (couplé véhicules)
class RecommendationEngine:
    def __init__(self, vehicle_repo: VehicleRepository):
        self.vehicle_repo = vehicle_repo
        self.collection = "vehicles"  # Hardcodé

    async def recommend(self, sentiment_result: SentimentResult):
        vehicles = await self.vehicle_repo.get_available()
        description = vehicle.to_description()  # Méthode spécifique Vehicle
        # ...

# APRÈS (générique multi-tenant)
class MultiTenantRecommendationEngine:
    def __init__(self, qdrant_client: QdrantClient, scoring_service: ScoringConfigService):
        self.qdrant = qdrant_client
        self.scoring_service = scoring_service

    async def recommend(
        self,
        tenant_id: str,
        product_id: str,
        product_description: str,
        sentiment_result: SentimentResult,
        top_k: int = 10
    ) -> List[str]:
        """
        Recommandation multi-tenant générique

        1. Récupérer collection Qdrant du tenant
        2. Vectoriser la description du produit
        3. Recherche similarité dans Qdrant
        4. Récupérer config scoring du tenant
        5. Appliquer scoring dynamique
        6. Retourner top_k product_ids
        """
        # 1. Collection dynamique
        collection_name = f"tenant_{tenant_id}"

        # 2. Vectorisation
        vector = await self.embed_text(product_description)

        # 3. Recherche similarité
        search_results = await self.qdrant.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=top_k * 2  # Sur-échantillonner pour scoring
        )

        # 4. Config scoring dynamique
        scoring_config = await self.scoring_service.get_active_config(tenant_id)

        # 5. Scoring dynamique
        scored_results = await self.apply_dynamic_scoring(
            search_results,
            scoring_config.scoring_criteria,
            sentiment_result
        )

        # 6. Top K
        top_products = scored_results[:top_k]
        return [p.product_id for p in top_products]

    async def apply_dynamic_scoring(
        self,
        results: List[ScoredPoint],
        criteria: List[Dict],
        sentiment: SentimentResult
    ) -> List[ScoredResult]:
        """
        Applique scoring basé sur critères JSON dynamiques

        criteria format:
        [
            {"name": "similarity", "weight": 0.70, "type": "system"},
            {"name": "sentiment_boost", "weight": 0.20, "type": "system"},
            {"name": "custom_field_1", "weight": 0.10, "type": "custom"}
        ]
        """
        scored = []
        for result in results:
            total_score = 0.0

            for criterion in criteria:
                if criterion["type"] == "system":
                    # Critères système prédéfinis
                    if criterion["name"] == "similarity":
                        total_score += result.score * criterion["weight"]
                    elif criterion["name"] == "sentiment_boost":
                        boost = 1.0 if sentiment.label == "positive" else 0.5
                        total_score += boost * criterion["weight"]

                elif criterion["type"] == "custom":
                    # Critères custom depuis payload Qdrant
                    field_value = result.payload.get(criterion["name"], 0.0)
                    total_score += float(field_value) * criterion["weight"]

            scored.append(ScoredResult(
                product_id=result.payload["product_id"],
                score=total_score
            ))

        return sorted(scored, key=lambda x: x.score, reverse=True)
```

#### 4.2 Refactoriser VectorStore (3 jours)

**Fichier:** `src/modules/module2_recommendation/vector_store.py`

**Changements:**
- Supprimer collection hardcodée
- Support collections dynamiques par tenant
- Méthodes pour créer/supprimer collections tenant

```python
class MultiTenantVectorStore:
    async def create_tenant_collection(self, tenant_id: str, vector_size: int = 768):
        """Créer collection Qdrant pour nouveau tenant"""
        collection_name = f"tenant_{tenant_id}"
        await self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )

    async def add_products(
        self,
        tenant_id: str,
        products: List[Dict]  # Format: [{product_id, description, metadata}, ...]
    ):
        """Ajouter/mettre à jour produits dans collection tenant"""
        collection_name = f"tenant_{tenant_id}"

        points = []
        for product in products:
            vector = await self.embed_text(product["description"])
            points.append(PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "product_id": product["product_id"],
                    "description": product["description"],
                    **product.get("metadata", {})
                }
            ))

        await self.qdrant.upsert(collection_name, points)
```

---

### 🟡 PHASE 5: Nouvelles Routes API (1 semaine)

**Objectif:** Créer les endpoints multi-tenant

#### 5.1 Endpoints Recommandation (2 jours)

**Fichier:** `src/api/routes/recommendations.py`

```python
@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Endpoint principal de recommandation multi-tenant

    Request:
    {
      "client_id": "client_123",
      "product_id": "prod_abc",
      "comment": "Excellent appartement très lumineux !",
      "top_k": 10
    }

    Response:
    {
      "client_id": "client_123",
      "product_ids": ["prod_xyz", "prod_def", ...]
    }
    """
    # 1. Analyse sentiment
    sentiment = await sentiment_service.analyze(request.comment)

    # 2. Récupérer description produit (depuis Qdrant ou cache)
    product_desc = await get_product_description(tenant_id, request.product_id)

    # 3. Recommandation
    recommendations = await recommendation_engine.recommend(
        tenant_id=tenant_id,
        product_id=request.product_id,
        product_description=product_desc,
        sentiment_result=sentiment,
        top_k=request.top_k
    )

    return RecommendationResponse(
        client_id=request.client_id,
        product_ids=recommendations
    )
```

#### 5.2 Endpoints Admin Tenants (2 jours)

```python
# Gestion Tenants
POST   /admin/tenants              # Créer tenant
GET    /admin/tenants              # Lister tenants
GET    /admin/tenants/{tenant_id}  # Détails tenant
PATCH  /admin/tenants/{tenant_id}  # Modifier tenant
DELETE /admin/tenants/{tenant_id}  # Supprimer tenant

# Gestion Scoring
GET    /admin/tenants/{tenant_id}/scoring       # Config actuelle
PUT    /admin/tenants/{tenant_id}/scoring       # Modifier config
GET    /admin/tenants/{tenant_id}/scoring/history  # Historique versions
```

#### 5.3 Endpoints Data Ingestion (2 jours)

```python
# Upload produits
POST /tenants/{tenant_id}/products
"""
Body:
{
  "products": [
    {
      "product_id": "prod_123",
      "description": "Appartement 3 pièces Paris 15ème...",
      "metadata": {
        "price": 450000,
        "location": "Paris",
        "custom_field": "value"
      }
    }
  ]
}
"""
```

---

### 🟡 PHASE 6: Frontend Admin Next.js (2 semaines)

**Objectif:** Interface d'administration pour gérer tenants et configs

#### 6.1 Setup Next.js (2 jours)

```bash
npx create-next-app@latest raas-admin-ui
cd raas-admin-ui
npm install @tanstack/react-query axios @nextui-org/react
```

#### 6.2 Pages Principales (8 jours)

```
pages/
├── /                          # Dashboard (métriques tenants)
├── /tenants                   # Liste tenants
├── /tenants/new               # Créer tenant
├── /tenants/[id]              # Détails tenant
├── /tenants/[id]/scoring      # Config scoring (IMPORTANT)
├── /tenants/[id]/products     # Upload produits
└── /login                     # OAuth2 Keycloak
```

#### 6.3 Scoring Config UI (3 jours) - CRITIQUE

**Interface pour modifier scoring dynamiquement:**

```tsx
// Interface de gestion des critères de scoring
const ScoringConfigEditor = () => {
  const [criteria, setCriteria] = useState([
    { name: "similarity", weight: 0.70, type: "system" },
    { name: "sentiment_boost", weight: 0.20, type: "system" },
    { name: "price_match", weight: 0.10, type: "custom" }
  ]);

  return (
    <div>
      {criteria.map((criterion, index) => (
        <CriterionRow
          key={index}
          criterion={criterion}
          onChange={(updated) => updateCriterion(index, updated)}
          onDelete={() => removeCriterion(index)}
        />
      ))}

      <Button onClick={addCustomCriterion}>
        + Ajouter Critère Custom
      </Button>

      <WeightValidator total={sumWeights(criteria)} />

      <Button onClick={saveScoringConfig}>
        Enregistrer Configuration
      </Button>
    </div>
  );
};
```

---

### 🟡 PHASE 7: Tests & QA (1 semaine)

#### 7.1 Tests Unitaires
- Services (TenantService, ScoringService)
- Middleware (Auth, Rate Limiting)
- RecommendationEngine

#### 7.2 Tests d'Intégration
- Flow complet: auth → recommendation → response
- Multi-tenant isolation
- Rate limiting

#### 7.3 Tests End-to-End
- Scénarios utilisateur complets

---

## 🎯 MVP Minimal Viable (Version Simplifiée)

Si vous voulez un MVP fonctionnel plus rapidement (~4 semaines au lieu de 10):

### MVP Phase 1 (1 semaine):
- ✅ Exécuter cleanup
- ✅ Créer modèles DB (Tenant, ScoringConfig)
- ✅ Créer TenantService basique

### MVP Phase 2 (1 semaine):
- ✅ Intégrer OAuth2 Keycloak (middleware)
- ✅ Endpoint `/recommendations` multi-tenant

### MVP Phase 3 (1 semaine):
- ✅ Refactoriser RecommendationEngine (basique, sans scoring dynamique)
- ✅ Support collections Qdrant par tenant

### MVP Phase 4 (1 semaine):
- ✅ API Admin basique (créer tenant, upload produits)
- ✅ Tests de base

**Fonctionnalités différées pour v2:**
- UI Admin Next.js (utiliser Postman/curl pour admin)
- Scoring dynamique (utiliser config hardcodée)
- Rate limiting avancé

---

## 📊 Checklist Complète

### Avant de Commencer
- [ ] Décider: MVP (4 semaines) ou Version Complète (10 semaines)?
- [ ] Exécuter scripts cleanup
- [ ] Valider que Keycloak fonctionne (`docker compose up keycloak`)

### Développement
- [ ] Phase 1: Nettoyage code
- [ ] Phase 2: Modèles DB
- [ ] Phase 3: OAuth2
- [ ] Phase 4: Module 2 refactoring
- [ ] Phase 5: API routes
- [ ] Phase 6: Frontend (optionnel pour MVP)
- [ ] Phase 7: Tests

### Déploiement
- [ ] Docker Compose avec Keycloak
- [ ] Variables d'environnement production
- [ ] Documentation API (Swagger)
- [ ] Guide onboarding nouveaux tenants

---

## 🚀 Prochaine Étape Immédiate

**Action recommandée:**

1. **Exécuter le cleanup** (30 min)
2. **Démarrer Phase 1** - Supprimer Celery + ELK (1 semaine)

Voulez-vous que je commence par:
- A) Exécuter les scripts de cleanup maintenant?
- B) Commencer Phase 1 (supprimer Celery)?
- C) Créer d'abord les modèles DB (Phase 2)?
- D) Autre chose?
