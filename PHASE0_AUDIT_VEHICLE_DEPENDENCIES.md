# 🔍 PHASE 0 - AUDIT DES DÉPENDANCES AU DOMAINE VÉHICULES

**Date:** 2025-01-15
**Auteur:** Audit automatisé
**Objectif:** Identifier tous les couplages au domaine véhicules avant transformation multi-tenant

---

## 📊 SYNTHÈSE EXÉCUTIVE

| Métrique | Valeur |
|----------|--------|
| **Fichiers Python couplés** | 15 |
| **Fichiers de configuration** | 3 |
| **Scripts** | 2 |
| **Fichiers SQL** | 1 |
| **Lignes de code à modifier/supprimer** | ~1500 |
| **Classes critiques** | 4 (Vehicle, VehicleRepository, VectorStore, RecommendationEngine) |
| **Méthodes critiques** | 12 |
| **Niveau de risque** | ⚠️ ÉLEVÉ |
| **Estimation effort** | 15-20 jours |

**Niveau de couplage:** 🔴 **FORT** - Le système est actuellement conçu exclusivement pour le domaine véhicules

---

## 🎯 FICHIERS CRITIQUES PAR CATÉGORIE

### 1. MODÈLES DATABASE (Haute Priorité)

#### `/home/user/AR_AS/src/database/models.py`

**Classe Vehicle (lignes 58-203)**
- ❌ **Supprimer** après transformation
- 145 lignes de code spécifiques au domaine
- Contient méthode `to_description()` hardcodée (lignes 149-202)

```python
# Code actuel à supprimer
class Vehicle(Base):
    __tablename__ = "vehicles"
    vehicle_id: Mapped[UUID] = mapped_column(primary_key=True)
    brand: Mapped[str]
    model: Mapped[str]
    year: Mapped[int]
    transmission_type: Mapped[Optional[str]]
    fuel_type: Mapped[Optional[str]]
    # ... 30+ autres colonnes spécifiques véhicules

    def to_description(self) -> str:
        """Génère description FR hardcodée pour véhicules"""
        # ... logique métier véhicule hardcodée
```

**Actions:**
1. Extraire `to_description()` vers service configurable
2. Créer interface `IProduct` abstraite
3. Implémenter factory pattern pour descriptions par tenant
4. Migrer données existantes avec `tenant_id`

---

**Classe Comment (lignes 205-231)**
- ✅ **Conserver** - Déjà abstrait avec `product_type` et `product_id`
- ⚠️ Ajouter index sur `(tenant_id, product_type, product_id)`

---

### 2. REPOSITORIES (Haute Priorité)

#### `/home/user/AR_AS/src/database/repositories.py`

**VehicleRepository (lignes 59-135)**
- ❌ **Supprimer** complètement
- 76 lignes de code spécifiques

**Méthodes à migrer:**
```python
# Méthodes actuelles
get_by_id(vehicle_id)           # → get_by_id(tenant_id, product_id)
get_available()                 # → get_available(tenant_id)
get_by_location(location)       # → get_by_location(tenant_id, location)
get_by_brand(brand)             # → get_by_metadata(tenant_id, key, value)
update_availability(id, status) # → update_metadata(tenant_id, id, metadata)
```

**Nouvelle architecture:**
```python
class ProductRepository:
    """Repository générique multi-tenant"""

    async def get_by_id(self, tenant_id: str, product_id: str):
        """Récupère produit avec filtrage tenant automatique"""
        pass

    async def get_all(self, tenant_id: str, filters: dict):
        """Liste produits avec filtres dynamiques par tenant"""
        pass
```

**Actions:**
1. Créer `ProductRepository` générique
2. Ajouter `tenant_id` à toutes les requêtes
3. Implémenter factory pattern par tenant
4. Supprimer instance globale `vehicle_repository` (ligne 168)

---

### 3. COLLECTIONS QDRANT (Haute Priorité)

#### `/home/user/AR_AS/src/config/settings.py` (ligne 82)
```python
# Actuel
qdrant_collection_vehicles: str = "vehicles"  # ❌ Hardcodé

# Nouveau
qdrant_collection_pattern: str = "tenant_{tenant_id}"  # ✅ Dynamique
```

---

#### `/home/user/AR_AS/src/modules/module2_recommendation/vector_store.py` (lignes 55-57)

```python
# Actuel - Mapping hardcodé
self.collections = {
    ProductType.VEHICLE: settings.qdrant_collection_vehicles,
}

# Nouveau - Factory dynamique
def get_collection_name(self, tenant_id: str) -> str:
    return f"tenant_{tenant_id}"
```

**Actions:**
1. Supprimer mapping `ProductType → collection`
2. Implémenter méthode `get_collection_name(tenant_id)`
3. Migrer collections existantes : `vehicles` → `tenant_default`
4. Ajouter création lazy des collections

---

#### `/home/user/AR_AS/src/api/app.py` (lignes 56-63)

```python
# Actuel - Création auto au démarrage
vector_store.create_collection_sync(ProductType.VEHICLE)  # ❌

# Nouveau - Création à la demande
# Plus de création automatique au démarrage
# Collections créées via endpoint admin POST /tenants/{id}
```

**Actions:**
1. Supprimer création automatique au démarrage
2. Implémenter endpoint admin pour création tenant
3. Créer collection Qdrant lors de l'onboarding tenant

---

### 4. MODULE 2 RECOMMENDATION (Haute Priorité)

#### `/home/user/AR_AS/src/modules/module2_recommendation/engine.py`

**Imports couplés (lignes 16-17)**
```python
from src.database.models import Vehicle  # ❌
from src.database.repositories import vehicle_repository  # ❌
```

**Méthode `_get_product_details()` (lignes 246-261) - CRITIQUE**
```python
# Actuel - Couplage fort
product = await vehicle_repository.get_by_id(product_id)
description = product.to_description()  # Méthode hardcodée
availability = product.disponible  # Propriété spécifique
reputation = product.note_moyenne  # Propriété spécifique

# Nouveau - Interface abstraite
product_service = self.product_service_factory.get(tenant_id)
product = await product_service.get_by_id(product_id)
description = await product_service.get_description(product)
metadata = await product_service.get_metadata(product)
```

**Actions:**
1. Supprimer imports directs Vehicle/VehicleRepository
2. Créer interface `IProductService` abstraite
3. Injecter `tenant_id` dans toutes les méthodes
4. Implémenter factory pattern pour ProductService par tenant

---

### 5. SCRIPTS (Moyenne Priorité)

#### `/home/user/AR_AS/scripts/init_vectors.py`

**Fonction `vectorize_vehicles()` (lignes 28-92) - ENTIÈREMENT COUPLÉE**

```python
# Actuel - Spécifique véhicules
def vectorize_vehicles():
    vehicles = vehicle_repository.get_all_sync(session)
    for vehicle in vehicles:
        description = vehicle.to_description()  # ❌ Hardcodé
        metadata = {
            "brand": vehicle.brand,  # ❌ Propriétés spécifiques
            "model": vehicle.model,
            # ...
        }
        vector_store.upsert_vectors_batch(ProductType.VEHICLE, batch)

# Nouveau - Générique multi-tenant
def vectorize_products(tenant_id: str, batch_size: int = 100):
    """Vectorise tous les produits d'un tenant"""
    product_service = ProductServiceFactory.get(tenant_id)
    products = await product_service.get_all_for_vectorization()

    for product in products:
        description = await product_service.get_description(product)
        metadata = await product_service.get_metadata(product)

        embedding = await embedding_service.generate(description)

        vector_store.upsert(
            collection_name=f"tenant_{tenant_id}",
            id=product.id,
            vector=embedding,
            payload={"id": product.id, "metadata": metadata}
        )
```

**Actions:**
1. Refactorer fonction en `vectorize_products(tenant_id)`
2. Ajouter CLI argument `--tenant-id`
3. Généraliser métadonnées (pas hardcodées)
4. Supprimer référence `ProductType.VEHICLE`

---

#### `/home/user/AR_AS/scripts/init_db.sql`

**Lignes 10-371 - Schéma SQL complet véhicules**
- ❌ **Archiver** comme référence historique
- Tables: `vehicle_make`, `vehicle_model`, `transmission_type`, `fuel_type`, `vehicles`, etc.
- 15 véhicules de test

**Actions:**
1. Créer nouveau script `init_db_multitenant.sql`
2. Créer tables: `tenants`, `scoring_configs`
3. Script de migration pour ajouter `tenant_id` aux données existantes
4. Conserver ancien script pour tests de migration

---

### 6. CONFIGURATION (Moyenne Priorité)

#### `/home/user/AR_AS/src/config/constants.py`

**Lignes 8, 21-24**
```python
# Actuel
PRODUCT_TYPE_VEHICLE = "vehicle"

class ProductType(str, Enum):
    VEHICLE = "vehicle"  # Seul type supporté

# Nouveau
class ProductType(str, Enum):
    VEHICLE = "vehicle"
    REAL_ESTATE = "real_estate"  # ✅ Ajouter
    RESTAURANT = "restaurant"     # ✅ Ajouter
    ECOMMERCE = "ecommerce"       # ✅ Ajouter
```

**Lignes 50-64 - Constantes spécifiques véhicules**
```python
# Actuel - Hardcodé
VEHICLE_FUEL_TYPES = ["essence", "diesel", "electrique", "hybride", "gpl"]
VEHICLE_TRANSMISSION_TYPES = ["manuelle", "automatique", "semi-automatique"]

# Nouveau - Configuration par tenant (JSON)
# Déplacer vers table scoring_configs ou fichiers par tenant
```

**Actions:**
1. Conserver `ProductType.VEHICLE` (backward compat)
2. Ajouter autres types de produits à l'enum
3. Déplacer constantes spécifiques vers config tenant
4. Créer système de configuration extensible

---

### 7. ROUTES API (Moyenne Priorité)

#### `/home/user/AR_AS/src/api/routes/recommendations.py` (ligne 151)

```python
# Actuel - Route dédiée véhicules
@router.get("/vehicles")
async def get_vehicle_recommendations(...):
    result = await orchestrator.process_recommendation_request(
        product_type="vehicle",  # ❌ Hardcodé
        ...
    )

# Nouveau - Route générique
@router.post("/tenants/{tenant_id}/recommendations")
async def get_recommendations(
    tenant_id: str,
    request: RecommendationRequest,
    tenant: Tenant = Depends(verify_tenant_access)  # ✅ Auth
):
    # tenant_id extrait du JWT OAuth2
    pass
```

**Actions:**
1. Supprimer route `/vehicles`
2. Créer route `/tenants/{tenant_id}/recommendations`
3. Ajouter middleware extraction `tenant_id` depuis JWT
4. Valider accès tenant via OAuth2

---

### 8. MODULE 3 ORCHESTRATION (Basse Priorité - À SUPPRIMER)

#### `/home/user/AR_AS/src/modules/module3_orchestration/tasks.py`

**Tâche `vectorize_products_task()` (lignes 219-233)**
- ❌ **Supprimer** avec tout le module Celery
- Remplacer par endpoints FastAPI async

---

### 9. DOCUMENTATION (Basse Priorité)

**Fichiers à mettre à jour:**
- `/home/user/AR_AS/README.md` (ligne 359)
- `/home/user/AR_AS/docs/ARCHITECTURE.md` (ligne 631)
- `/home/user/AR_AS/docs/mermaid/*.mmd` (diagrammes)

**Actions:**
1. Mettre à jour tous les exemples
2. Remplacer "véhicules" par "produits"
3. Ajouter diagrammes multi-tenant
4. Créer guide de migration

---

## 🗂️ MATRICE DE DÉPENDANCES

| Fichier | Niveau Couplage | Priorité | Action | Effort |
|---------|-----------------|----------|--------|--------|
| `src/database/models.py` (Vehicle) | 🔴 Très Fort | P0 | Supprimer | 3j |
| `src/database/repositories.py` (VehicleRepository) | 🔴 Très Fort | P0 | Supprimer | 2j |
| `src/modules/module2_recommendation/engine.py` | 🔴 Très Fort | P0 | Refactorer | 5j |
| `src/modules/module2_recommendation/vector_store.py` | 🟠 Fort | P1 | Refactorer | 2j |
| `scripts/init_vectors.py` | 🟠 Fort | P1 | Refactorer | 1j |
| `src/config/constants.py` | 🟡 Moyen | P2 | Modifier | 0.5j |
| `src/api/routes/recommendations.py` | 🟡 Moyen | P2 | Refactorer | 1j |
| `src/api/app.py` | 🟡 Moyen | P2 | Modifier | 0.5j |
| `scripts/init_db.sql` | 🟢 Faible | P3 | Archiver | 0.5j |
| Documentation | 🟢 Faible | P3 | Mettre à jour | 2j |

**Légende Priorité:**
- **P0:** Bloquant - Doit être fait en premier
- **P1:** Important - Nécessaire pour l'architecture multi-tenant
- **P2:** Utile - Améliore l'expérience
- **P3:** Nice to have - Peut être différé

---

## 📋 PLAN D'ACTION SÉQUENTIEL

### Étape 1: Abstraction (Semaine 1)
- [ ] Créer interface `IProduct` avec méthodes abstraites
- [ ] Créer interface `IProductService` pour logique métier
- [ ] Créer `ProductServiceFactory` avec stratégie par tenant
- [ ] Extraire `to_description()` en service configurable
- [ ] Ajouter champ `tenant_id` à tous les modèles

### Étape 2: Nouveaux Modèles (Semaine 1-2)
- [ ] Créer modèle `Tenant` (PostgreSQL)
- [ ] Créer modèle `ScoringConfig` avec critères dynamiques (JSON)
- [ ] Créer migrations Alembic
- [ ] Script de migration pour ajouter `tenant_id` aux véhicules existants

### Étape 3: Refactoring Repositories (Semaine 2)
- [ ] Créer `ProductRepository` générique
- [ ] Implémenter factory pattern pour repositories
- [ ] Ajouter filtrage automatique par `tenant_id`
- [ ] Supprimer `VehicleRepository`
- [ ] Supprimer instance globale `vehicle_repository`

### Étape 4: Refactoring Engine (Semaine 2-3)
- [ ] Supprimer imports directs `Vehicle`, `vehicle_repository`
- [ ] Injecter `ProductService` via dependency injection
- [ ] Ajouter `tenant_id` à toutes les méthodes
- [ ] Refactorer `_get_product_details()` pour utiliser `ProductService`
- [ ] Tests unitaires multi-tenant

### Étape 5: Collections Qdrant (Semaine 3)
- [ ] Implémenter méthode `get_collection_name(tenant_id)`
- [ ] Migrer collection existante `vehicles` → `tenant_default`
- [ ] Supprimer création automatique au démarrage
- [ ] Créer endpoint admin pour création tenant + collection
- [ ] Tests d'isolation entre collections

### Étape 6: API Routes (Semaine 3)
- [ ] Setup Keycloak dans Docker Compose
- [ ] Créer middleware d'extraction `tenant_id` depuis JWT
- [ ] Créer routes `/tenants/{tenant_id}/*`
- [ ] Supprimer routes dédiées véhicules
- [ ] Tests d'authentification OAuth2

### Étape 7: Scripts & Utilitaires (Semaine 4)
- [ ] Refactorer `init_vectors.py` en `vectorize_products(tenant_id)`
- [ ] Créer nouveau script `init_db_multitenant.sql`
- [ ] Script de migration des données existantes
- [ ] CLI avec support `--tenant-id`

### Étape 8: Tests & Documentation (Semaine 4)
- [ ] Tests E2E multi-tenant
- [ ] Tests d'isolation entre tenants
- [ ] Mettre à jour toute la documentation
- [ ] Guide de migration pour nouveaux tenants
- [ ] Benchmarks de performance

---

## ⚠️ RISQUES IDENTIFIÉS

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| **Perte de données pendant migration** | 🔴 Critique | Faible | Backup complet avant migration |
| **Performance dégradée avec multi-tenant** | 🟠 Élevé | Moyenne | Benchmarks avant/après, index optimisés |
| **Complexité OAuth2 + Keycloak** | 🟠 Élevé | Moyenne | POC Keycloak avant intégration complète |
| **Breaking changes pour clients existants** | 🟡 Moyen | Élevée | Versioning API (v1 → v2), période de transition |
| **Isolation insuffisante entre tenants** | 🔴 Critique | Faible | Tests approfondis, code review sécurité |

---

## 🎯 CRITÈRES DE SUCCÈS

### Fonctionnels
- ✅ Aucune référence hardcodée au domaine "véhicules" dans le code
- ✅ Support de minimum 3 types de produits (véhicules, immobilier, restaurants)
- ✅ Isolation complète entre tenants (données, collections, cache)
- ✅ Configuration scoring 100% dynamique par tenant
- ✅ Authentification OAuth2 fonctionnelle avec Keycloak

### Techniques
- ✅ Tests coverage ≥ 85%
- ✅ Performance: P95 latency <200ms (cache miss)
- ✅ Pas de régression de performance vs système actuel
- ✅ Support concurrent de 10+ tenants sans dégradation
- ✅ Documentation complète et à jour

### Opérationnels
- ✅ Migration des données existantes réussie sans perte
- ✅ Rollback plan documenté et testé
- ✅ Monitoring par tenant fonctionnel
- ✅ Guide d'onboarding nouveaux tenants
- ✅ Zero downtime deployment

---

## 📊 EFFORT TOTAL ESTIMÉ

| Phase | Durée | Charge |
|-------|-------|--------|
| Étape 1: Abstraction | 1 semaine | 5j |
| Étape 2: Nouveaux Modèles | 1 semaine | 3j |
| Étape 3: Refactoring Repositories | 1 semaine | 3j |
| Étape 4: Refactoring Engine | 1.5 semaines | 5j |
| Étape 5: Collections Qdrant | 1 semaine | 3j |
| Étape 6: API Routes | 1 semaine | 4j |
| Étape 7: Scripts & Utilitaires | 1 semaine | 3j |
| Étape 8: Tests & Documentation | 1 semaine | 4j |
| **TOTAL** | **8.5 semaines** | **30 jours** |

**Note:** Estimation basée sur 1 développeur expérimenté à temps plein.

---

## 🔄 PROCHAINES ÉTAPES IMMÉDIATES

1. ✅ **Valider ce plan** avec l'équipe technique
2. ⏭️ **Créer backup** complet de la DB actuelle
3. ⏭️ **Setup Keycloak** dans Docker Compose local
4. ⏭️ **Créer branche** `feature/multi-tenant-core`
5. ⏭️ **Commencer Étape 1** : Abstraction

---

**Document généré automatiquement par l'audit Phase 0**
**Version:** 1.0
**Date:** 2025-01-15
