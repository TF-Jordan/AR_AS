# 🚀 Perspectives : Vers un Système de Recommandation Universel

> **Document de présentation** - Architecture Multi-Tenant pour AR_AS
> 
> Ce document explique comment transformer AR_AS en un système de recommandation centralisé capable de servir plusieurs plateformes simultanément.

---

## 📖 Table des Matières

1. [Le Problème Initial](#-le-problème-initial)
2. [La Solution Proposée](#-la-solution-proposée)
3. [Comment ça Marche ?](#-comment-ça-marche-)
4. [Les Composants Clés](#-les-composants-clés)
5. [Isolation des Données](#-isolation-des-données)
6. [Les Modèles d'Intelligence Artificielle](#-les-modèles-dintelligence-artificielle)
7. [Critères de Scoring Personnalisables](#-critères-de-scoring-personnalisables)
8. [Interface d'Administration](#-interface-dadministration)
9. [Exemple Concret](#-exemple-concret)
10. [Avantages de cette Architecture](#-avantages-de-cette-architecture)
11. [Feuille de Route](#-feuille-de-route)

---

## 🎯 Le Problème Initial

### Situation Actuelle

Aujourd'hui, **AR_AS** est un système de recommandation conçu **uniquement pour les véhicules**. Il fonctionne très bien, mais il a une limitation importante :

```
┌─────────────────────────────────────┐
│         AR_AS Actuel                │
│  ┌─────────────────────────────┐    │
│  │  Recommandation Véhicules   │    │  ← Un seul domaine !
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**Le problème** : Si l'entreprise veut aussi recommander des restaurants, des appartements ou des produits e-commerce, il faudrait créer un nouveau système à chaque fois !

### L'Analogie Simple 🍕

Imaginez un chef cuisinier qui ne sait faire **que des pizzas**. Si un client veut des sushis, il faut engager un autre chef. C'est coûteux et peu pratique !

**L'idéal** : Un chef polyvalent qui peut cuisiner n'importe quel plat selon la demande.

---

## 💡 La Solution Proposée

### Vision : Recommendation-as-a-Service (RaaS)

Nous allons transformer AR_AS en un **système de recommandation universel** capable de servir **n'importe quelle plateforme** de l'entreprise.

```
┌─────────────────────────────────────────────────────────────┐
│              AR_AS Multi-Tenant (Futur)                     │
│                                                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │ Véhicules │  │ Immobilier│  │Restaurants│  │E-commerce│ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘ │
│        │              │              │              │       │
│        └──────────────┴──────────────┴──────────────┘       │
│                              │                              │
│                    ┌─────────▼─────────┐                    │
│                    │  Moteur Unique    │                    │
│                    │  de Recommandation│                    │
│                    │   Intelligent     │                    │
│                    └───────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### Qu'est-ce qu'un "Tenant" ?

Un **tenant** (locataire en anglais) représente une **plateforme cliente** du système. Chaque tenant :
- A ses propres données (produits, avis clients)
- A ses propres critères de recommandation
- Est complètement isolé des autres tenants

**Exemple** : 
- Tenant "Véhicules" → recommande des voitures
- Tenant "Restaurants" → recommande des restaurants
- Tenant "Immobilier" → recommande des appartements

---

## 🔄 Comment ça Marche ?

### Le Flux Simplifié

Voici comment le système traite une demande de recommandation :

```
    ① Client écrit un avis
           │
           ▼
    ┌─────────────────┐
    │ "Super resto,   │
    │ ambiance top !" │
    └────────┬────────┘
             │
             ▼
    ② Le système analyse le sentiment
    ┌─────────────────┐
    │  😊 Positif     │     ← Intelligence Artificielle
    │  Score: 0.92    │
    └────────┬────────┘
             │
             ▼
    ③ Transformation en vecteur mathématique
    ┌─────────────────┐
    │ [0.23, 0.87,    │     ← "Embedding" = représentation
    │  0.12, 0.45...] │        numérique du texte
    └────────┬────────┘
             │
             ▼
    ④ Recherche de produits similaires
    ┌─────────────────┐
    │  🔍 Qdrant      │     ← Base de données vectorielle
    │  (recherche     │
    │  de similarité) │
    └────────┬────────┘
             │
             ▼
    ⑤ Calcul du score final
    ┌─────────────────┐
    │ Critères :      │
    │ • Similarité 50%│     ← Configurable par plateforme !
    │ • Note 30%      │
    │ • Distance 20%  │
    └────────┬────────┘
             │
             ▼
    ⑥ Résultats personnalisés
    ┌─────────────────┐
    │ 1. Le Bouchon   │
    │ 2. Chez Marcel  │     ← Top recommandations
    │ 3. La Trattoria │
    └─────────────────┘
```

### Explication Étape par Étape

| Étape | Nom | Explication Simple |
|-------|-----|---------------------|
| ① | Entrée utilisateur | Le client donne son avis ou sa recherche |
| ② | Analyse de sentiment | L'IA comprend si c'est positif, négatif ou neutre |
| ③ | Embedding | Le texte devient une liste de nombres (comme une empreinte digitale du texte) |
| ④ | Recherche vectorielle | On cherche les produits qui ont une "empreinte" similaire |
| ⑤ | Scoring | On applique les critères de la plateforme pour classer les résultats |
| ⑥ | Résultats | Les meilleures recommandations sont envoyées au client |

---

## 🧱 Les Composants Clés

### Vue d'Ensemble de l'Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │Véhicules │  │Immobilier│  │Restaurant│  │E-commerce│             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼─────────────┼───────────────────┘
        │             │             │             │
        └─────────────┴──────┬──────┴─────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    🔐 PASSERELLE API                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Authentification│  │  Identification │  │   Routage vers  │      │
│  │   (Qui es-tu?)  │  │  du Tenant      │  │   le bon service│      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  🧠 MODULE 1  │     │  🎯 MODULE 2  │     │  📊 MODULE 3  │
│   Analyse de  │     │  Génération   │     │   Moteur de   │
│   Sentiment   │     │  d'Embeddings │     │    Scoring    │
│               │     │               │     │               │
│ "C'est bien!" │     │ Texte → [0.2, │     │ Pondération   │
│   → 😊 0.9    │     │  0.8, 0.1...] │     │ des critères  │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    💾 STOCKAGE DES DONNÉES                          │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │    Qdrant       │  │   PostgreSQL    │  │     Redis       │      │
│  │  (Vecteurs)     │  │ (Données)       │  │   (Cache)       │      │
│  │                 │  │                 │  │                 │      │
│  │ Recherche ultra │  │ Configurations, │  │ Réponses rapides│      │
│  │   rapide        │  │ historiques     │  │ (mise en cache) │      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

### Tableau des Composants

| Composant | Rôle | Analogie Simple |
|-----------|------|-----------------|
| **Passerelle API** | Point d'entrée unique | Le réceptionniste d'un hôtel |
| **Analyseur de Sentiment** | Comprend les émotions | Un psychologue qui écoute |
| **Générateur d'Embeddings** | Transforme le texte en nombres | Un traducteur universel |
| **Moteur de Scoring** | Calcule les scores finaux | Un juge avec des critères |
| **Qdrant** | Stocke et recherche les vecteurs | Une bibliothèque ultra-rapide |
| **PostgreSQL** | Stocke les configurations | Un classeur bien organisé |
| **Redis** | Cache les résultats fréquents | Une mémoire à court terme |

---

## 🔒 Isolation des Données

### Pourquoi l'Isolation est Cruciale ?

Chaque plateforme doit avoir ses données **complètement séparées** pour :
- 🔐 **Sécurité** : Les données de "Véhicules" ne doivent pas être accessibles par "Restaurants"
- 🧹 **Propreté** : Pas de mélange entre domaines différents
- 📊 **Performance** : Chaque plateforme optimisée indépendamment

### Comment on Isole les Données ?

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BASE DE DONNÉES (PostgreSQL)                     │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Schema:         │  │ Schema:         │  │ Schema:         │      │
│  │ vehicules       │  │ restaurants     │  │ immobilier      │      │
│  │ ─────────────── │  │ ─────────────── │  │ ─────────────── │      │
│  │ • produits      │  │ • produits      │  │ • produits      │      │
│  │ • avis          │  │ • avis          │  │ • avis          │      │
│  │ • config        │  │ • config        │  │ • config        │      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
│         🚗                  🍕                   🏠                  │
│                                                                      │
│  Chaque "schema" = un compartiment étanche !                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Analogie Simple 🏨

Imaginez un **hôtel** :
- Chaque client (tenant) a sa propre chambre (schema)
- Les chambres sont séparées par des murs (isolation)
- Le client ne peut pas entrer dans la chambre d'un autre
- Mais tous utilisent le même hôtel (système central)

---

## 🧠 Les Modèles d'Intelligence Artificielle

Nous proposons **deux approches** pour les modèles d'IA :

### Approche A : Un Modèle pour Tous 🤝

```
┌─────────────────────────────────────────────────┐
│           UN SEUL MODÈLE PARTAGÉ                │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Véhicules │  │Restaurants│ │Immobilier│      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │
│       └─────────────┼─────────────┘             │
│                     │                           │
│                     ▼                           │
│         ┌───────────────────┐                   │
│         │  🧠 Modèle Unique │                   │
│         │  (Généraliste)    │                   │
│         └───────────────────┘                   │
└─────────────────────────────────────────────────┘
```

| Avantages ✅ | Inconvénients ❌ |
|-------------|-----------------|
| Simple à gérer | Moins précis pour vocabulaires spécialisés |
| Économe en ressources | Pas de personnalisation |
| Rapide à déployer | Un seul modèle pour tous les domaines |
| Maintenance facile | |

**Idéal pour** : Démarrage rapide, domaines similaires

---

### Approche B : Un Modèle par Plateforme 🎯

```
┌─────────────────────────────────────────────────┐
│        MODÈLES SPÉCIALISÉS PAR TENANT           │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Véhicules │  │Restaurants│ │Immobilier│      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │
│       ▼             ▼             ▼             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ 🚗 IA   │  │ 🍕 IA   │  │ 🏠 IA   │         │
│  │ Auto    │  │ Food    │  │ Immo    │         │
│  └─────────┘  └─────────┘  └─────────┘         │
│                                                 │
│  Chaque modèle "parle" le langage du domaine ! │
└─────────────────────────────────────────────────┘
```

| Avantages ✅ | Inconvénients ❌ |
|-------------|-----------------|
| Très précis par domaine | Plus complexe à gérer |
| Vocabulaire spécialisé | Plus de ressources (mémoire) |
| Évolutif (fine-tuning) | Maintenance plus lourde |
| Personnalisable | Déploiement plus long |

**Idéal pour** : Domaines très différents, besoin de haute précision

---

### Notre Recommandation 💡

> **Commencer simple, évoluer ensuite !**
> 
> 1. **Phase 1** : Déployer avec l'Approche A (modèle unique)
> 2. **Phase 2** : Identifier les tenants qui ont besoin de plus de précision
> 3. **Phase 3** : Ajouter des modèles spécialisés pour ces tenants

---

## ⚖️ Critères de Scoring Personnalisables

### Le Problème

Chaque domaine a des critères de qualité **différents** :

| Domaine | Ce qui compte le plus |
|---------|----------------------|
| 🚗 Véhicules | Prix, kilométrage, année, marque |
| 🍕 Restaurants | Note, distance, type de cuisine, prix moyen |
| 🏠 Immobilier | Prix/m², localisation, surface, nombre de pièces |

### La Solution : Scoring Configurable

Chaque plateforme peut définir **ses propres critères** avec des **poids personnalisés** :

```
┌─────────────────────────────────────────────────────────────────────┐
│                   CONFIGURATION DU SCORING                          │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🚗 VÉHICULES                                               │    │
│  │  ───────────────────────────────────────────────────────────│    │
│  │  • Similarité     ████████████████████░░░░░░░░░░  50%       │    │
│  │  • Disponibilité  ██████████░░░░░░░░░░░░░░░░░░░░  25%       │    │
│  │  • Réputation     ██████░░░░░░░░░░░░░░░░░░░░░░░░  15%       │    │
│  │  • Prix           ████░░░░░░░░░░░░░░░░░░░░░░░░░░  10%       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🍕 RESTAURANTS                                             │    │
│  │  ───────────────────────────────────────────────────────────│    │
│  │  • Similarité     ████████████████░░░░░░░░░░░░░░  40%       │    │
│  │  • Note moyenne   ████████████░░░░░░░░░░░░░░░░░░  30%       │    │
│  │  • Distance       ████████░░░░░░░░░░░░░░░░░░░░░░  20%       │    │
│  │  • Prix moyen     ████░░░░░░░░░░░░░░░░░░░░░░░░░░  10%       │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Comment ça Fonctionne ?

```
    Produit A                         Score Final
    ─────────                         ───────────
    
    Similarité: 0.8   × 50% = 0.40
    Disponible: 1.0   × 25% = 0.25      0.40 + 0.25 + 0.12 + 0.08
    Réputation: 0.8   × 15% = 0.12      ─────────────────────────
    Prix:       0.8   × 10% = 0.08      Score = 0.85 / 1.00
    
    ➡️ Ce produit obtient un score de 85% !
```

---

## 🎛️ Interface d'Administration

### Deux Façons de Gérer les Tenants

#### 1. Dashboard Visuel (pour les Administrateurs) 🖥️

```
┌─────────────────────────────────────────────────────────────────────┐
│  🎛️ DASHBOARD ADMIN - RaaS Platform                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  📊 VUE D'ENSEMBLE                                          │    │
│  │  ─────────────────────────────                              │    │
│  │  Tenants actifs: 4        Requêtes/jour: 12,450             │    │
│  │  Temps moyen: 45ms        Cache hit: 78%                    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  📋 LISTE DES TENANTS                                       │    │
│  │  ─────────────────────────────────────────────────────────  │    │
│  │                                                             │    │
│  │  ┌─────────┬──────────────┬──────────┬──────────┬────────┐ │    │
│  │  │ Statut  │ Nom          │ Domaine  │ Requêtes │ Action │ │    │
│  │  ├─────────┼──────────────┼──────────┼──────────┼────────┤ │    │
│  │  │ 🟢      │ Véhicules    │ Auto     │ 5,230    │ ⚙️     │ │    │
│  │  │ 🟢      │ Restaurants  │ Food     │ 4,120    │ ⚙️     │ │    │
│  │  │ 🟢      │ Immobilier   │ Realty   │ 2,890    │ ⚙️     │ │    │
│  │  │ 🟡      │ E-commerce   │ Retail   │ 210      │ ⚙️     │ │    │
│  │  └─────────┴──────────────┴──────────┴──────────┴────────┘ │    │
│  │                                                             │    │
│  │                              [+ Nouveau Tenant]             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Fonctionnalités** :
- ✅ Créer/modifier/supprimer des tenants
- ✅ Configurer les critères de scoring (glisser-déposer)
- ✅ Visualiser les statistiques en temps réel
- ✅ Tester les recommandations

---

#### 2. API Self-Service (pour les Développeurs) 💻

Les développeurs peuvent aussi gérer les tenants via des appels API :

```bash
# Créer un nouveau tenant
POST /api/v1/admin/tenants
{
  "name": "Restaurants Lyon",
  "slug": "resto-lyon",
  "domain": "restaurants",
  "scoring": {
    "criteria": [
      {"name": "similarité", "weight": 0.5},
      {"name": "note", "weight": 0.3},
      {"name": "distance", "weight": 0.2}
    ]
  }
}

# Réponse
{
  "tenant_id": "abc-123-xyz",
  "api_key": "sk_live_xxxx",
  "status": "active"
}
```

---

## 📝 Exemple Concret

### Scénario : L'Entreprise Ajoute une Plateforme Restaurants

#### Étape 1 : Création du Tenant

L'administrateur crée le tenant "Restaurants" via le dashboard :

```
┌─────────────────────────────────────────────┐
│  ➕ NOUVEAU TENANT                          │
│  ─────────────────────────────────          │
│                                             │
│  Nom:     [Restaurants Lyon          ]      │
│  Slug:    [resto-lyon                ]      │
│  Domaine: [restaurants               ]      │
│                                             │
│  Critères de scoring:                       │
│  ┌─────────────┬─────────────────────┐      │
│  │ Similarité  │ ████████████░░ 40%  │      │
│  │ Note        │ ██████████░░░░ 30%  │      │
│  │ Distance    │ ████████░░░░░░ 20%  │      │
│  │ Prix        │ ████░░░░░░░░░░ 10%  │      │
│  └─────────────┴─────────────────────┘      │
│                                             │
│           [Créer le Tenant]                 │
└─────────────────────────────────────────────┘
```

#### Étape 2 : Import des Données

La plateforme Restaurants importe ses établissements :

```json
// POST /api/v1/tenants/resto-lyon/items/bulk
[
  {
    "id": "1",
    "nom": "Le Bouchon Lyonnais",
    "description": "Cuisine traditionnelle lyonnaise, ambiance chaleureuse",
    "note": 4.7,
    "type_cuisine": "Lyonnaise",
    "prix_moyen": 35
  },
  {
    "id": "2",
    "nom": "Sushi Palace",
    "description": "Restaurant japonais moderne, sushis frais du jour",
    "note": 4.5,
    "type_cuisine": "Japonaise",
    "prix_moyen": 28
  }
  // ... autres restaurants
]
```

#### Étape 3 : Demande de Recommandation

Un client cherche un restaurant :

```json
// POST /api/v1/tenants/resto-lyon/recommendations
{
  "query": "Je cherche un bon restaurant italien pas trop cher avec terrasse",
  "location": {"lat": 45.7640, "lng": 4.8357},
  "top_k": 5
}
```

#### Étape 4 : Réponse Personnalisée

```json
{
  "status": "success",
  "recommendations": [
    {
      "rang": 1,
      "nom": "La Trattoria",
      "score": 0.89,
      "note": 4.6,
      "prix_moyen": 22,
      "distance_km": 0.5,
      "pourquoi": "Cuisine italienne authentique, terrasse ensoleillée"
    },
    {
      "rang": 2,
      "nom": "Pizzeria Bella",
      "score": 0.82,
      "note": 4.4,
      "prix_moyen": 18,
      "distance_km": 0.8
    }
    // ... 3 autres résultats
  ],
  "sentiment_query": 0.75,
  "temps_traitement_ms": 52
}
```

---

## ✨ Avantages de cette Architecture

### Pour l'Entreprise

| Avantage | Explication |
|----------|-------------|
| 💰 **Économie** | Un seul système à maintenir au lieu de plusieurs |
| 🚀 **Rapidité** | Nouvelle plateforme opérationnelle en quelques heures |
| 📈 **Scalabilité** | Supporte des centaines de plateformes |
| 🔧 **Maintenabilité** | Corrections et améliorations profitent à tous |

### Pour les Plateformes

| Avantage | Explication |
|----------|-------------|
| ⚙️ **Personnalisation** | Critères de scoring adaptés à leur domaine |
| 🔒 **Isolation** | Données complètement séparées |
| 📊 **Monitoring** | Tableau de bord dédié |
| 🤖 **IA de qualité** | Accès aux derniers modèles sans effort |

### Pour les Clients Finaux

| Avantage | Explication |
|----------|-------------|
| 🎯 **Pertinence** | Recommandations vraiment adaptées |
| ⚡ **Rapidité** | Réponses en quelques millisecondes |
| 😊 **Expérience** | Meilleure découverte de produits |

---

## 📅 Feuille de Route

### Phase 1 : Fondations (3 semaines)

```
Semaine 1-2:
├── ✅ Architecture multi-tenant
├── ✅ Isolation des données (Qdrant, PostgreSQL, Redis)
└── ✅ Middleware d'authentification

Semaine 3:
├── ✅ API d'administration (CRUD tenants)
└── ✅ Provisioning automatique
```

### Phase 2 : Fonctionnalités (3 semaines)

```
Semaine 4:
├── ✅ Moteur de scoring configurable
└── ✅ Import/export de données

Semaine 5-6:
├── ✅ Dashboard admin (MVP)
├── ✅ Interface de test
└── ✅ Documentation
```

### Phase 3 : Optimisations (Optionnel, 4 semaines)

```
Semaine 7-8:
├── ⏳ Support modèles personnalisés par tenant
└── ⏳ Pipeline de fine-tuning

Semaine 9-10:
├── ⏳ Monitoring avancé par tenant
└── ⏳ Optimisations de performance
```

---

## 🎓 Résumé pour la Présentation

### En Une Phrase

> **AR_AS Multi-Tenant** transforme un système de recommandation spécialisé en une **plateforme universelle** capable de servir n'importe quel domaine (véhicules, restaurants, immobilier, etc.) avec une **isolation totale des données** et des **critères personnalisables**.

### Les 5 Points Clés à Retenir

1. **🎯 Un système, plusieurs plateformes** - Plus besoin de recréer un système pour chaque domaine
2. **🔒 Isolation complète** - Les données de chaque plateforme sont strictement séparées
3. **⚙️ Scoring personnalisable** - Chaque plateforme définit ses propres critères
4. **🧠 IA flexible** - Modèle unique ou spécialisé selon les besoins
5. **🎛️ Administration simple** - Dashboard visuel + API pour les développeurs

---

## 📚 Annexes

### Glossaire

| Terme | Définition |
|-------|------------|
| **Tenant** | Une plateforme cliente du système (ex: "Véhicules", "Restaurants") |
| **Embedding** | Représentation numérique d'un texte sous forme de vecteur |
| **Scoring** | Processus de calcul du score de pertinence d'une recommandation |
| **Qdrant** | Base de données spécialisée dans la recherche de similarité |
| **API** | Interface permettant aux applications de communiquer entre elles |
| **Multi-tenant** | Architecture où plusieurs clients partagent un même système |

### Questions Fréquentes

**Q: Combien de plateformes peut-on gérer ?**
> R: L'architecture est conçue pour supporter des centaines de tenants. Les limites sont principalement liées aux ressources serveur.

**Q: Les données sont-elles sécurisées ?**
> R: Oui, chaque tenant a son propre espace de stockage isolé. Il est techniquement impossible d'accéder aux données d'un autre tenant.

**Q: Peut-on ajouter de nouveaux critères de scoring ?**
> R: Oui, le système est extensible. De nouveaux types de critères peuvent être ajoutés sans modifier les tenants existants.

---

*Document rédigé le 06 février 2026*
*Projet AR_AS - Perspectives Multi-Tenant v1.0*
