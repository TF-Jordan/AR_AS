# Module 4 - Système de Ranking Multicritère pour Livreurs
## Plan d'Implémentation Détaillé

---

## 📋 I. CONTEXTE ET OBJECTIF

### Workflow de la Plateforme

```
1. CLIENT crée une ANNONCE
   ├─ Point de ramassage (lat, lon)
   ├─ Point de livraison (lat, lon)
   ├─ Type de véhicule demandé
   └─ Autres détails (poids, dimensions, etc.)

2. LIVREURS souscrivent à l'annonce
   └─ Liste des candidats intéressés

3. PLATEFORME appelle notre API
   ├─ Envoie l'annonce
   └─ Envoie la liste des livreurs

4. NOTRE SYSTÈME classe les livreurs
   ├─ Filtrage spatial (ellipse sphérique)
   ├─ Calcul des poids (AHP)
   └─ Ranking multicritère (TOPSIS)

5. RETOUR de la liste classée
   └─ Top N livreurs recommandés avec scores
```

### Caractéristiques Clés
- ✅ **Stateless**: Pas de stockage de données livreurs en base
- ✅ **Service de ranking pur**: Reçoit des données → Retourne un classement
- ✅ **Indépendant**: Ne partage pas la DB avec le système véhicules
- ✅ **Basé sur le Modèle 4**: AHP + TOPSIS

---

## 📊 II. FORMAT DES DONNÉES

### A. Requête d'Entrée (POST /api/v1/livreurs/rank)

```json
{
  "annonce": {
    "annonce_id": "uuid-de-l-annonce",
    "point_ramassage": {
      "latitude": 3.8480,
      "longitude": 11.5021,
      "adresse": "Bastos, Yaoundé"
    },
    "point_livraison": {
      "latitude": 3.8667,
      "longitude": 11.5167,
      "adresse": "Centre-ville, Yaoundé"
    },
    "type_vehicule_demande": "moto",  // ou "voiture", "camion", "velo"
    "poids_colis_kg": 5.0,
    "dimensions_cm": {
      "longueur": 30,
      "largeur": 20,
      "hauteur": 15
    },
    "delai_souhaite_minutes": 60,
    "description": "Livraison de documents urgents"
  },
  "livreurs_candidats": [
    {
      "livreur_id": "uuid-livreur-1",
      "nom_commercial": "Express Delivery",
      "position_actuelle": {
        "latitude": 3.8520,
        "longitude": 11.5050
      },
      "reputation": 8.7,        // sur 10
      "nombre_livraisons": 150,
      "taux_reussite": 0.95,    // 95%
      "type_vehicule": "moto",
      "capacite_max_kg": 10,
      "disponible": true,
      "temps_reponse_moyen_min": 5,
      "rayon_action_km": 15
    },
    {
      "livreur_id": "uuid-livreur-2",
      "nom_commercial": "Flash Livraison",
      "position_actuelle": {
        "latitude": 3.8600,
        "longitude": 11.5100
      },
      "reputation": 9.2,
      "nombre_livraisons": 230,
      "taux_reussite": 0.98,
      "type_vehicule": "voiture",
      "capacite_max_kg": 50,
      "disponible": true,
      "temps_reponse_moyen_min": 8,
      "rayon_action_km": 25
    }
  ],
  "preferences_classement": {
    "proximite_weight": "auto",      // ou valeur fixe 0.0-1.0
    "reputation_weight": "auto",
    "capacite_weight": "auto",
    "type_vehicule_weight": "auto",
    "top_k": 5,                      // nombre de résultats souhaités
    "tolerance_spatiale_km": 1.5,    // pour l'ellipse
    "methode_poids": "AHP"           // ou "manual"
  }
}
```

### B. Réponse de Sortie

```json
{
  "status": "success",
  "annonce_id": "uuid-de-l-annonce",
  "timestamp": "2025-01-15T12:34:56Z",
  "methode_utilisee": {
    "filtrage": "ellipse_spherique",
    "ponderation": "AHP",
    "classement": "TOPSIS"
  },
  "statistiques_filtrage": {
    "candidats_initiaux": 10,
    "candidats_apres_filtrage": 7,
    "candidats_elimines": 3,
    "raison_elimination": [
      {
        "livreur_id": "uuid-livreur-x",
        "raison": "hors_zone_ellipse",
        "distance_totale_km": 25.3,
        "distance_max_km": 15.0
      }
    ]
  },
  "poids_criteres": {
    "proximite_geographique": 0.558,
    "reputation": 0.264,
    "capacite": 0.122,
    "type_vehicule": 0.057,
    "coherence_ahp": {
      "CR": 0.067,
      "est_coherent": true
    }
  },
  "livreurs_classes": [
    {
      "rang": 1,
      "livreur_id": "uuid-livreur-2",
      "nom_commercial": "Flash Livraison",
      "score_final": 0.892,
      "details_scores": {
        "proximite": {
          "distance_ramassage_km": 1.2,
          "distance_livraison_km": 1.8,
          "distance_totale_km": 3.0,
          "score_normalise": 0.95
        },
        "reputation": {
          "valeur": 9.2,
          "score_normalise": 0.92
        },
        "capacite": {
          "capacite_kg": 50,
          "adequation_colis": true,
          "score_normalise": 1.0
        },
        "type_vehicule": {
          "type": "voiture",
          "adequation_demande": false,
          "score_normalise": 0.75
        }
      },
      "distances_topsis": {
        "distance_ideale_positive": 0.015,
        "distance_ideale_negative": 0.178
      },
      "recommandation": "EXCELLENT",
      "commentaire": "Meilleur équilibre entre proximité et réputation"
    },
    {
      "rang": 2,
      "livreur_id": "uuid-livreur-1",
      "nom_commercial": "Express Delivery",
      "score_final": 0.845,
      "details_scores": {
        "proximite": {
          "distance_ramassage_km": 0.8,
          "distance_livraison_km": 1.2,
          "distance_totale_km": 2.0,
          "score_normalise": 1.0
        },
        "reputation": {
          "valeur": 8.7,
          "score_normalise": 0.87
        },
        "capacite": {
          "capacite_kg": 10,
          "adequation_colis": true,
          "score_normalise": 0.8
        },
        "type_vehicule": {
          "type": "moto",
          "adequation_demande": true,
          "score_normalise": 1.0
        }
      },
      "distances_topsis": {
        "distance_ideale_positive": 0.045,
        "distance_ideale_negative": 0.165
      },
      "recommandation": "TRES_BON",
      "commentaire": "Plus proche mais capacité limitée"
    }
  ],
  "processing_time_ms": 45.3
}
```

---

## 🏗️ III. ARCHITECTURE DU MODULE 4

### Structure des Dossiers

```
src/modules/module4_livreur_ranking/
├── __init__.py
├── schemas.py                 # Pydantic models pour API
├── spatial_filter.py          # Phase 1: Filtrage ellipse sphérique
├── ahp_calculator.py          # Phase 2: AHP pour poids
├── topsis_ranker.py           # Phase 3: TOPSIS pour classement
├── orchestrator.py            # Orchestrateur principal
├── utils.py                   # Utilitaires (Haversine, etc.)
└── constants.py               # Constantes (échelle Saaty, etc.)

src/api/routes/
└── livreur_ranking.py         # Routes API pour le ranking
```

### Diagramme de Flux

```
┌─────────────────────────────────────────────────────────────┐
│                    API POST /rank                           │
│              (Annonce + Livreurs candidats)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   1. ORCHESTRATOR     │
         │  Validation des       │
         │  données d'entrée     │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ 2. SPATIAL FILTER     │
         │ • Calcul Haversine    │
         │ • Ellipse sphérique   │
         │ • Filtrage candidats  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  3. AHP CALCULATOR    │
         │ • Matrice comparaison │
         │ • Calcul poids        │
         │ • Vérif cohérence CR  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  4. TOPSIS RANKER     │
         │ • Normalisation       │
         │ • Pondération         │
         │ • Solutions idéales   │
         │ • Scores similarité   │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  5. RESPONSE BUILDER  │
         │ • Formatage résultats │
         │ • Ajout métadonnées   │
         │ • Recommandations     │
         └───────────┬───────────┘
                     │
                     ▼
                JSON Response
```

---

## 🔢 IV. ALGORITHMES À IMPLÉMENTER

### A. Phase 1: Filtrage Spatial (spatial_filter.py)

```python
class SpatialFilter:
    """
    Filtre les livreurs en utilisant une ellipse sphérique.
    """

    def __init__(self, earth_radius_km: float = 6371.0):
        self.earth_radius = earth_radius_km

    def haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calcule la distance géodésique (formule de Haversine).

        Formule:
        d = 2R × arcsin(√(sin²((φ₂-φ₁)/2) + cos(φ₁)cos(φ₂)sin²((λ₂-λ₁)/2)))

        Returns: distance en km
        """
        pass

    def filter_by_ellipse(
        self,
        livreurs: List[Livreur],
        point_ramassage: Point,
        point_livraison: Point,
        tolerance_km: float = 1.5
    ) -> Tuple[List[Livreur], List[Dict]]:
        """
        Filtre selon: d(L, F1) + d(L, F2) ≤ Dmax
        où Dmax = d(F1, F2) + 2×tolerance

        Returns: (livreurs_eligibles, livreurs_rejetes)
        """
        pass
```

### B. Phase 2: AHP (ahp_calculator.py)

```python
class AHPCalculator:
    """
    Implémente la méthode Analytic Hierarchy Process.
    """

    # Échelle de Saaty (1-9)
    SAATY_SCALE = {
        1: "Également important",
        3: "Modérément plus important",
        5: "Fortement plus important",
        7: "Très fortement plus important",
        9: "Extrêmement plus important"
    }

    # Indices de cohérence aléatoires
    RI = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
          7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

    def build_comparison_matrix(
        self,
        criteria: List[str],
        preferences: Dict[str, str]  # "auto" ou valeurs manuelles
    ) -> np.ndarray:
        """
        Construit la matrice de comparaison par paires.

        Par défaut (mode auto):
        - Proximité vs Réputation: 3 (proximité plus importante)
        - Proximité vs Capacité: 5
        - Proximité vs Type véhicule: 7
        - Réputation vs Capacité: 3
        - Réputation vs Type véhicule: 5
        - Capacité vs Type véhicule: 3
        """
        pass

    def calculate_weights(
        self,
        matrix: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Calcule les poids normalisés.

        Méthode: moyenne des colonnes normalisées

        Returns: (poids, CR)
        """
        pass

    def check_consistency(
        self,
        matrix: np.ndarray,
        weights: np.ndarray
    ) -> Tuple[float, bool]:
        """
        Vérifie la cohérence (Consistency Ratio).

        CR = CI / RI < 0.1 → cohérent
        CI = (λmax - n) / (n - 1)

        Returns: (CR, est_coherent)
        """
        pass
```

### C. Phase 3: TOPSIS (topsis_ranker.py)

```python
class TOPSISRanker:
    """
    Implémente TOPSIS pour le classement multicritère.
    """

    def normalize_matrix(
        self,
        decision_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Normalisation vectorielle:
        rᵢⱼ = xᵢⱼ / √(Σxᵢⱼ²)
        """
        pass

    def apply_weights(
        self,
        normalized_matrix: np.ndarray,
        weights: np.ndarray
    ) -> np.ndarray:
        """
        Pondération: vᵢⱼ = wⱼ × rᵢⱼ
        """
        pass

    def calculate_ideal_solutions(
        self,
        weighted_matrix: np.ndarray,
        beneficial_criteria: List[int]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        A⁺ = (max vᵢⱼ) pour critères bénéfiques
        A⁻ = (min vᵢⱼ) pour critères bénéfiques

        Returns: (ideal_positive, ideal_negative)
        """
        pass

    def calculate_distances(
        self,
        weighted_matrix: np.ndarray,
        ideal_positive: np.ndarray,
        ideal_negative: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Distance euclidienne:
        D⁺ᵢ = √(Σ(vᵢⱼ - vⱼ⁺)²)
        D⁻ᵢ = √(Σ(vᵢⱼ - vⱼ⁻)²)

        Returns: (distances_positive, distances_negative)
        """
        pass

    def calculate_similarity_scores(
        self,
        distances_positive: np.ndarray,
        distances_negative: np.ndarray
    ) -> np.ndarray:
        """
        Score de similarité:
        Cᵢ = D⁻ᵢ / (D⁺ᵢ + D⁻ᵢ)

        Returns: scores (0-1, plus proche de 1 = meilleur)
        """
        pass

    def rank(
        self,
        livreurs: List[Livreur],
        annonce: Annonce,
        weights: np.ndarray,
        top_k: int = 5
    ) -> List[RankedLivreur]:
        """
        Workflow complet TOPSIS.
        """
        pass
```

---

## 🎯 V. CRITÈRES DE RANKING

### Matrice Décisionnelle

Pour m livreurs et 4 critères:

| Livreur | Proximité (km) | Réputation (/10) | Capacité (kg) | Type Véhicule |
|---------|----------------|------------------|---------------|---------------|
| L1      | 2.0            | 8.7              | 10            | moto (0.3)    |
| L2      | 3.0            | 9.2              | 50            | voiture (0.8) |
| L3      | 1.5            | 7.5              | 5             | velo (0.1)    |

### Conversion Type de Véhicule

```python
VEHICLE_TYPE_SCORES = {
    "velo": 0.1,
    "moto": 0.3,
    "voiture": 0.8,
    "camion": 1.0
}
```

### Critères Bénéfiques vs Coût

- **À minimiser (coût):** Proximité (distance)
- **À maximiser (bénéfique):** Réputation, Capacité, Type véhicule

---

## 📝 VI. SCHÉMAS PYDANTIC

```python
# schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class Point(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    adresse: Optional[str] = None

class Annonce(BaseModel):
    annonce_id: str
    point_ramassage: Point
    point_livraison: Point
    type_vehicule_demande: Literal["velo", "moto", "voiture", "camion"]
    poids_colis_kg: float = Field(..., gt=0)
    dimensions_cm: Optional[dict] = None
    delai_souhaite_minutes: Optional[int] = None
    description: Optional[str] = None

class LivreurCandidat(BaseModel):
    livreur_id: str
    nom_commercial: str
    position_actuelle: Point
    reputation: float = Field(..., ge=0, le=10)
    nombre_livraisons: int = Field(..., ge=0)
    taux_reussite: float = Field(..., ge=0, le=1)
    type_vehicule: Literal["velo", "moto", "voiture", "camion"]
    capacite_max_kg: float = Field(..., gt=0)
    disponible: bool = True
    temps_reponse_moyen_min: Optional[int] = None
    rayon_action_km: Optional[float] = None

class PreferencesClassement(BaseModel):
    proximite_weight: Union[Literal["auto"], float] = "auto"
    reputation_weight: Union[Literal["auto"], float] = "auto"
    capacite_weight: Union[Literal["auto"], float] = "auto"
    type_vehicule_weight: Union[Literal["auto"], float] = "auto"
    top_k: int = Field(default=5, ge=1, le=20)
    tolerance_spatiale_km: float = Field(default=1.5, gt=0)
    methode_poids: Literal["AHP", "manual"] = "AHP"

class RankingRequest(BaseModel):
    annonce: Annonce
    livreurs_candidats: List[LivreurCandidat]
    preferences_classement: Optional[PreferencesClassement] = None

class DetailScores(BaseModel):
    proximite: dict
    reputation: dict
    capacite: dict
    type_vehicule: dict

class LivreurClasse(BaseModel):
    rang: int
    livreur_id: str
    nom_commercial: str
    score_final: float
    details_scores: DetailScores
    distances_topsis: dict
    recommandation: Literal["EXCELLENT", "TRES_BON", "BON", "MOYEN", "FAIBLE"]
    commentaire: str

class RankingResponse(BaseModel):
    status: Literal["success", "partial_success", "error"]
    annonce_id: str
    timestamp: datetime
    methode_utilisee: dict
    statistiques_filtrage: dict
    poids_criteres: dict
    livreurs_classes: List[LivreurClasse]
    processing_time_ms: float
    warnings: Optional[List[str]] = None
```

---

## 🔌 VII. ROUTES API

```python
# src/api/routes/livreur_ranking.py

from fastapi import APIRouter, HTTPException, status
from src.modules.module4_livreur_ranking import Orchestrator

router = APIRouter(prefix="/livreurs", tags=["Livreur Ranking"])

@router.post("/rank", response_model=RankingResponse)
async def rank_livreurs(request: RankingRequest):
    """
    Classe les livreurs candidats selon la méthodologie AHP + TOPSIS.

    **Workflow:**
    1. Filtrage spatial (ellipse sphérique)
    2. Calcul des poids (AHP)
    3. Classement multicritère (TOPSIS)

    **Returns:** Liste classée des meilleurs livreurs
    """
    orchestrator = Orchestrator()
    result = orchestrator.process_ranking(request)
    return result

@router.post("/rank/explain", response_model=ExplainedRankingResponse)
async def explain_ranking(request: RankingRequest):
    """
    Version détaillée avec explication étape par étape.
    Utile pour le debugging et la compréhension.
    """
    pass

@router.get("/health")
async def health_check():
    """Health check pour le module de ranking."""
    return {"status": "healthy", "module": "livreur_ranking"}
```

---

## ⚙️ VIII. CONFIGURATION

### Ajout au .env

```bash
# Module 4 - Livreur Ranking
LIVREUR_RANKING_ENABLED=true
LIVREUR_RANKING_DEFAULT_TOP_K=5
LIVREUR_RANKING_DEFAULT_TOLERANCE_KM=1.5
LIVREUR_RANKING_EARTH_RADIUS_KM=6371.0

# AHP Settings
AHP_DEFAULT_PROXIMITE_WEIGHT=3.0
AHP_DEFAULT_REPUTATION_WEIGHT=3.0
AHP_CONSISTENCY_THRESHOLD=0.1

# TOPSIS Settings
TOPSIS_NORMALIZATION_METHOD=vector  # or min-max
```

---

## 🧪 IX. EXEMPLE DE TEST COMPLET

```python
# test_ranking.py

import requests

# Données de test
payload = {
    "annonce": {
        "annonce_id": "test-001",
        "point_ramassage": {
            "latitude": 3.8480,
            "longitude": 11.5021,
            "adresse": "Bastos, Yaoundé"
        },
        "point_livraison": {
            "latitude": 3.8667,
            "longitude": 11.5167,
            "adresse": "Centre-ville, Yaoundé"
        },
        "type_vehicule_demande": "moto",
        "poids_colis_kg": 5.0
    },
    "livreurs_candidats": [
        {
            "livreur_id": "liv-001",
            "nom_commercial": "Express Delivery",
            "position_actuelle": {
                "latitude": 3.8520,
                "longitude": 11.5050
            },
            "reputation": 8.7,
            "nombre_livraisons": 150,
            "taux_reussite": 0.95,
            "type_vehicule": "moto",
            "capacite_max_kg": 10,
            "disponible": true
        },
        {
            "livreur_id": "liv-002",
            "nom_commercial": "Flash Livraison",
            "position_actuelle": {
                "latitude": 3.8600,
                "longitude": 11.5100
            },
            "reputation": 9.2,
            "nombre_livraisons": 230,
            "taux_reussite": 0.98,
            "type_vehicule": "voiture",
            "capacite_max_kg": 50,
            "disponible": true
        }
    ]
}

# Appel API
response = requests.post(
    "http://localhost:8000/api/v1/livreurs/rank",
    json=payload
)

print(response.json())
```

---

## 📊 X. MÉTRIQUES ET MONITORING

### Métriques à Tracker

```python
# À ajouter dans le code
from prometheus_client import Counter, Histogram, Gauge

ranking_requests_total = Counter(
    'livreur_ranking_requests_total',
    'Total ranking requests'
)

ranking_duration_seconds = Histogram(
    'livreur_ranking_duration_seconds',
    'Time spent processing ranking'
)

candidates_filtered = Gauge(
    'livreur_candidates_after_spatial_filter',
    'Number of candidates after spatial filtering'
)

ahp_consistency_ratio = Gauge(
    'livreur_ranking_ahp_consistency_ratio',
    'AHP consistency ratio'
)
```

---

## 🚀 XI. PLAN D'IMPLÉMENTATION PAR ÉTAPES

### Étape 1: Structure de Base (2h)
- [ ] Créer la structure de dossiers
- [ ] Définir les schémas Pydantic
- [ ] Créer les fichiers vides avec docstrings

### Étape 2: Filtrage Spatial (3h)
- [ ] Implémenter Haversine
- [ ] Implémenter l'ellipse sphérique
- [ ] Tests unitaires

### Étape 3: AHP Calculator (4h)
- [ ] Matrice de comparaison
- [ ] Calcul des poids
- [ ] Vérification cohérence
- [ ] Tests avec données du modèle 4

### Étape 4: TOPSIS Ranker (4h)
- [ ] Normalisation
- [ ] Solutions idéales
- [ ] Scores de similarité
- [ ] Tests

### Étape 5: Orchestrator (2h)
- [ ] Intégration des 3 phases
- [ ] Gestion des erreurs
- [ ] Formatage réponses

### Étape 6: Routes API (2h)
- [ ] Endpoint /rank
- [ ] Endpoint /explain
- [ ] Validation des données

### Étape 7: Tests d'Intégration (3h)
- [ ] Tests end-to-end
- [ ] Tests avec exemples du modèle 4
- [ ] Tests de performance

### Étape 8: Documentation (2h)
- [ ] Swagger/OpenAPI
- [ ] Exemples d'utilisation
- [ ] Guide pour l'équipe plateforme

**TOTAL ESTIMÉ: ~22 heures**

---

## 📤 XII. LIVRABLE POUR L'ÉQUIPE PLATEFORME

### Document d'Intégration

```markdown
# API de Ranking de Livreurs - Guide d'Intégration

## Endpoint Principal
POST http://your-domain.com/api/v1/livreurs/rank

## Authentication
Bearer Token requis (si applicable)

## Rate Limiting
100 requêtes/minute par IP

## Format des Données
Voir sections II.A et II.B ci-dessus

## Exemples de Code
- Python (requests)
- JavaScript (fetch)
- cURL

## Codes d'Erreur
- 400: Données invalides
- 422: Validation échouée
- 500: Erreur serveur

## Support
contact@your-domain.com
```

---

## ✅ XIII. CHECKLIST DE VALIDATION

Avant de livrer à la plateforme:

- [ ] Tous les tests passent
- [ ] Performance < 500ms pour 20 candidats
- [ ] CR de AHP toujours < 0.1
- [ ] Documentation API complète
- [ ] Exemples de requêtes testés
- [ ] Gestion d'erreurs robuste
- [ ] Logs structurés (JSON)
- [ ] Monitoring configuré
- [ ] Déploiement en staging validé

---

**Questions ?**
Contactez l'équipe de développement du système de recommandation.
