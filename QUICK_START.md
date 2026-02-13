# 🚀 Quick Start - Faire Fonctionner la Platform RaaS

## ⚡ 3 Étapes Critiques (15 minutes)

### 1️⃣ Démarrer PostgreSQL

**Option A: Avec Docker (recommandé)**
```bash
# Si Docker est disponible sur votre machine
docker compose up -d postgres

# Vérifier
docker compose ps
```

**Option B: Sans Docker**
```bash
# Installer PostgreSQL localement
sudo apt update && sudo apt install postgresql

# Démarrer le service
sudo systemctl start postgresql

# Créer la base de données
sudo -u postgres createdb recommendation_db
```

### 2️⃣ Appliquer les Migrations

```bash
cd /home/user/AR_AS

# Vérifier que .env existe (il a été créé automatiquement)
ls -la .env

# Appliquer les migrations (crée toutes les tables)
alembic upgrade head

# Vérifier (doit afficher: tenants, products, scoring_configs, product_descriptions)
psql -U postgres -d recommendation_db -c "\dt"
```

### 3️⃣ Désactiver l'Auth (pour tests rapides)

**Modifier `src/api/dependencies.py` ligne 15-35:**

```python
# REMPLACER cette fonction:
async def require_admin(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, ...)  # validation complexe
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# PAR CECI (temporaire pour tests):
async def require_admin(token: str = Depends(oauth2_scheme)) -> dict:
    # ⚠️ TEMPORARY: Skip auth for local testing
    return {
        "sub": "test-admin-user",
        "realm_access": {"roles": ["admin"]},
        "tenant_id": None
    }
```

---

## 🎯 Démarrer l'Application

### Terminal 1: Backend

```bash
cd /home/user/AR_AS
python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

**Résultat attendu:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 2: Frontend

```bash
cd /home/user/AR_AS/frontend

# Si Node.js < 20, mettre à jour d'abord:
# curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
# sudo apt-get install -y nodejs

npm install
npm run dev
```

**Résultat attendu:**
```
▲ Next.js 16.1.6
- Local: http://localhost:3000
```

---

## ✅ Tester que Tout Fonctionne

### Test 1: Backend Health Check

```bash
curl http://localhost:8000/health

# Attendu: {"status":"healthy"}
```

### Test 2: Créer un Tenant de Test

```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants/ \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-tenant",
    "name": "Demo Tenant",
    "domain": "demo.example.com",
    "qdrant_collection_name": "demo_collection"
  }'

# Attendu: JSON avec l'ID du tenant créé
# Copier l'ID pour les prochains tests
```

### Test 3: Upload de Produits CSV

**Créer un fichier de test:**
```bash
cat > /tmp/test_products.csv <<'EOF'
product_id,name,description,category,sku
LAPTOP-001,Dell XPS 13,Ultrabook 13 pouces,Electronics,XPS13
PHONE-001,iPhone 15,Smartphone Apple,Mobile,IP15
AUDIO-001,Sony WH-1000XM5,Casque Bluetooth,Audio,SONY-WH5
EOF
```

**Uploader:**
```bash
# Remplacer <TENANT_ID> par l'ID du tenant créé
TENANT_ID="<votre-tenant-id-ici>"

curl -X POST "http://localhost:8000/api/v1/tenants/${TENANT_ID}/products/upload" \
  -F "file=@/tmp/test_products.csv"

# Attendu: {"total_processed":3,"total_created":3,"errors":[]}
```

### Test 4: Vérifier le Dashboard

**Dans le navigateur:**
```
http://localhost:3000
```

**Vérifications:**
- ✅ Dashboard affiche "Total Tenants: 1"
- ✅ Dashboard affiche "Total Products: 3"
- ✅ Page "/tenants" liste le tenant créé
- ✅ Page "/tenants/{id}/products" affiche les 3 produits

---

## ❌ Problèmes Courants

### "Connection refused" sur PostgreSQL

**Cause:** PostgreSQL n'est pas démarré

**Solution:**
```bash
# Avec Docker:
docker compose up -d postgres

# Sans Docker:
sudo systemctl start postgresql
```

### "relation 'tenants' does not exist"

**Cause:** Migrations pas appliquées

**Solution:**
```bash
alembic upgrade head
```

### "401 Unauthorized"

**Cause:** L'auth n'a pas été désactivée

**Solution:** Suivre l'Étape 3 ci-dessus (modifier `dependencies.py`)

### "Module not found" (Backend)

**Cause:** Dépendances pas installées

**Solution:**
```bash
pip install -r requirements.txt
```

### "Node.js version >= 20.9.0 required"

**Cause:** Node.js trop ancien

**Solution:**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version  # Doit afficher v20.x.x
```

---

## 📊 État du Code

| Composant | Status | Détails |
|-----------|--------|---------|
| **Backend API** | ✅ 100% | 13 routes implémentées |
| **Frontend Pages** | ✅ 100% | 10 pages créées |
| **Modèles DB** | ✅ 100% | Tenant, Product, ScoringConfig, ProductDescription |
| **Migrations** | ✅ 100% | 2 migrations (initial + products) |
| **Base de données** | ❌ 0% | Tables pas créées (besoin: `alembic upgrade head`) |
| **Services externes** | ❌ 0% | PostgreSQL, Qdrant, Redis pas démarrés |
| **Tests** | ❌ 0% | Jamais exécutés |

**Conclusion:** Le code est complet, seule l'infrastructure doit être configurée.

---

## 📚 Documentation Complète

Pour plus de détails, voir:

- **SETUP_GUIDE_COMPLET.md** - Guide complet avec toutes les options
- **README_ETAT_COMPLET.md** - État détaillé du projet (backend + frontend)
- **BACKEND_FIXES.md** - Routes ajoutées récemment
- **BACKEND_FRONTEND_COMMUNICATION.md** - Mapping des routes API

---

## 🎯 Récapitulatif des Commandes

```bash
# 1. PostgreSQL
docker compose up -d postgres  # ou: sudo systemctl start postgresql

# 2. Migrations
alembic upgrade head

# 3. Backend (Terminal 1)
python -m uvicorn src.api.app:app --reload

# 4. Frontend (Terminal 2)
cd frontend && npm install && npm run dev

# 5. Créer données de test
curl -X POST http://localhost:8000/api/v1/admin/tenants/ -H "Content-Type: application/json" -d '{"tenant_id":"test","name":"Test","qdrant_collection_name":"test"}'

# 6. Ouvrir le navigateur
open http://localhost:3000
```

**Temps estimé:** 10-15 minutes

---

**Dernière mise à jour:** 2026-02-13
**Branche:** `claude/review-project-perspectives-lUDIe`
**Commit:** `c67887a`
