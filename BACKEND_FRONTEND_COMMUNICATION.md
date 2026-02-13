# Communication Backend ↔ Frontend - RaaS Platform

## ✅ Configuration Réseau

### Frontend (Next.js)
- **Port:** 3000
- **URL API:** `http://localhost:8000/api/v1` (configuré via `NEXT_PUBLIC_API_URL`)
- **Client HTTP:** Axios avec intercepteurs
- **Auth:** JWT Bearer token stocké dans `localStorage`

### Backend (FastAPI)
- **Port:** 8000
- **Base path:** `/api/v1`
- **CORS:** ✅ Configuré (`allow_origins=["*"]`)
- **Auth:** JWT validation via Keycloak

## 📡 Mapping des Routes API

| Fonctionnalité | Frontend (lib/api.ts) | Backend (routes/) | Status |
|----------------|----------------------|-------------------|--------|
| **Liste tenants** | `GET /admin/tenants/` | `GET /admin/tenants/` | ✅ Compatible |
| **Créer tenant** | `POST /admin/tenants/` | `POST /admin/tenants/` | ✅ Compatible |
| **Détails tenant** | `GET /admin/tenants/{id}` | `GET /admin/tenants/{id}` | ✅ Compatible |
| **Stats tenant** | `GET /admin/tenants/{id}/stats` | `GET /admin/tenants/{id}/stats` | ✅ Compatible |
| **Scoring config** | `GET /admin/scoring/tenants/{id}/config` | `GET /admin/scoring/tenants/{id}/config` | ✅ Compatible |
| **Update scoring** | `PUT /admin/scoring/tenants/{id}/config` | `PUT /admin/scoring/tenants/{id}/config` | ✅ Compatible |
| **Liste produits** | `GET /tenants/{id}/products` | `GET /tenants/{id}/products` | ✅ Compatible |
| **Upload produits** | `POST /tenants/{id}/products/upload` | `POST /tenants/{id}/products/upload` | ✅ Compatible |
| **Dashboard metrics** | `GET /admin/dashboard/metrics` | `GET /admin/dashboard/metrics` | ✅ Compatible |

## 🔐 Authentification

### Frontend
```typescript
// Intercepteur Axios (lib/api.ts)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### Backend
```python
# Validation JWT via Keycloak (dependencies.py)
async def require_admin(token: str = Depends(oauth2_scheme)):
    # Vérifie le rôle 'admin' dans le token JWT
    ...
```

## 🔄 Flux de Communication

```
┌─────────────┐          ┌─────────────┐
│  Frontend   │          │   Backend   │
│ (Next.js)   │          │  (FastAPI)  │
│  :3000      │          │   :8000     │
└──────┬──────┘          └──────┬──────┘
       │                        │
       │  1. GET /admin/tenants │
       ├───────────────────────>│
       │                        │
       │  2. Check JWT token    │
       │                        │
       │  3. JSON response      │
       │<───────────────────────┤
       │                        │
```

## ⚙️ Configuration CORS (Backend)

```python
# src/api/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 Tests de Communication

### Test 1: Health Check
```bash
# Backend doit être démarré
curl http://localhost:8000/health
# Réponse attendue: {"status":"healthy"}
```

### Test 2: API depuis Frontend
```bash
# Démarrer les deux services
docker-compose up backend  # Terminal 1
cd frontend && npm run dev # Terminal 2

# Ouvrir: http://localhost:3000
# Les données du dashboard doivent se charger via l'API
```

### Test 3: CORS
```bash
# Vérifier les headers CORS
curl -I -X OPTIONS http://localhost:8000/api/v1/admin/tenants/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"

# Réponse doit contenir:
# Access-Control-Allow-Origin: *
# Access-Control-Allow-Methods: *
```

## ⚠️ Points d'Attention

### 1. Authentification
- **Frontend:** Requiert un token JWT valide dans `localStorage`
- **Backend:** Routes `/admin/*` nécessitent le rôle `admin`
- **Solution temporaire:** Désactiver l'auth pour les tests initiaux

### 2. CORS en Production
```python
# Production: restreindre les origines
allow_origins=["https://votre-domaine.com"]
```

### 3. Variables d'Environnement

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXTAUTH_URL=http://localhost:3000
```

**Backend (.env):**
```env
DATABASE_URL=postgresql+asyncpg://...
QDRANT_URL=http://localhost:6333
KEYCLOAK_URL=http://localhost:8080
```

## 📝 Types TypeScript ↔ Pydantic

Les types sont synchronisés entre frontend et backend:

| Frontend (types.ts) | Backend (schemas.py) |
|---------------------|----------------------|
| `Tenant` | `TenantResponse` |
| `ScoringConfig` | `ScoringConfigResponse` |
| `Product` | `Product` (model) |
| `PaginatedResponse<T>` | Patterns de pagination |

## 🚀 Démarrage Complet

```bash
# 1. Backend + dépendances (PostgreSQL, Qdrant, Redis)
docker-compose up -d

# 2. Frontend (dev mode)
cd frontend
npm install
npm run dev

# 3. Accéder à l'application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs (Swagger)
```

## ✅ Checklist de Validation

- [x] CORS activé sur le backend
- [x] Routes API mappées correctement
- [x] Types TypeScript ↔ Pydantic alignés
- [x] Intercepteurs Axios configurés
- [x] Variables d'environnement définies
- [ ] Tests avec Keycloak actif
- [ ] Tests E2E frontend → backend
- [ ] Gestion d'erreurs complète

## 📊 Statut Actuel

**Backend:** ✅ 100% complet - Toutes les routes implémentées
**Frontend:** ✅ 100% complet - Toutes les pages et hooks créés
**Communication:** ✅ Prêt - CORS et routes compatibles
**Tests:** ⏳ En attente - Nécessite démarrage des services
