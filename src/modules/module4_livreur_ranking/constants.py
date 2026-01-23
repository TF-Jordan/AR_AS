"""
Constants for Module 4 - Livreur Ranking System

Ordre d'importance des critères:
1. Proximité géographique (le plus important)
2. Capacité de transport
3. Type de véhicule
4. Réputation
"""

from enum import Enum
from typing import Dict

# Earth radius in kilometers (for Haversine calculations)
EARTH_RADIUS_KM = 6371.0

# Delivery types
class TypeLivraison(str, Enum):
    """Types de livraison supportés."""
    STANDARD = "standard"
    EXPRESS = "express"
    SAMEDAY = "sameday"

# Vehicle types
class TypeVehicule(str, Enum):
    """Types de véhicule."""
    VELO = "velo"
    MOTO = "moto"
    VOITURE = "voiture"
    CAMION = "camion"

# Vehicle type scores (for TOPSIS normalization)
# Camion = meilleure capacité/polyvalence
VEHICLE_TYPE_SCORES: Dict[str, float] = {
    TypeVehicule.VELO: 0.1,
    TypeVehicule.MOTO: 0.3,
    TypeVehicule.VOITURE: 0.8,
    TypeVehicule.CAMION: 1.0,
}

# Saaty Scale for AHP (1-9 scale)
SAATY_SCALE = {
    1: "Également important",
    2: "Entre également et modérément important",
    3: "Modérément plus important",
    4: "Entre modérément et fortement important",
    5: "Fortement plus important",
    6: "Entre fortement et très fortement important",
    7: "Très fortement plus important",
    8: "Entre très fortement et extrêmement important",
    9: "Extrêmement plus important",
}

# Random Index (RI) for AHP consistency check
RANDOM_INDEX = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}

# AHP Consistency Ratio threshold
AHP_CONSISTENCY_THRESHOLD = 0.1  # CR < 0.1 is acceptable

# =============================================================================
# AHP COMPARISON MATRICES
# =============================================================================
# Ordre des critères: [proximité, capacité, type_véhicule, réputation]
# Ordre d'importance: Proximité > Capacité > Type véhicule > Réputation
#
# Chaque valeur représente l'importance relative sur l'échelle de Saaty (1-9)
# Exemple: proximite_vs_capacite = 3 signifie proximité 3x plus important que capacité

# STANDARD delivery: approche équilibrée mais proximité reste prioritaire
AHP_MATRIX_STANDARD = {
    # Proximité vs autres (le plus important)
    "proximite_vs_capacite": 2,           # proximité légèrement plus important
    "proximite_vs_type_vehicule": 3,      # proximité modérément plus important
    "proximite_vs_reputation": 4,         # proximité fortement plus important
    # Capacité vs autres (2ème plus important)
    "capacite_vs_type_vehicule": 2,       # capacité légèrement plus important
    "capacite_vs_reputation": 3,          # capacité modérément plus important
    # Type véhicule vs réputation (3ème)
    "type_vehicule_vs_reputation": 2,     # type légèrement plus important
}

# EXPRESS delivery: emphase forte sur proximité
AHP_MATRIX_EXPRESS = {
    "proximite_vs_capacite": 3,
    "proximite_vs_type_vehicule": 4,
    "proximite_vs_reputation": 5,
    "capacite_vs_type_vehicule": 2,
    "capacite_vs_reputation": 3,
    "type_vehicule_vs_reputation": 2,
}

# SAMEDAY delivery: emphase maximale sur proximité
AHP_MATRIX_SAMEDAY = {
    "proximite_vs_capacite": 4,
    "proximite_vs_type_vehicule": 5,
    "proximite_vs_reputation": 6,
    "capacite_vs_type_vehicule": 2,
    "capacite_vs_reputation": 3,
    "type_vehicule_vs_reputation": 2,
}

# Mapping delivery type to AHP matrix
AHP_MATRICES = {
    TypeLivraison.STANDARD: AHP_MATRIX_STANDARD,
    TypeLivraison.EXPRESS: AHP_MATRIX_EXPRESS,
    TypeLivraison.SAMEDAY: AHP_MATRIX_SAMEDAY,
}

# Default spatial tolerance (km) by delivery type
# Zone d'éligibilité autour de l'ellipse ramassage-livraison
SPATIAL_TOLERANCE_KM = {
    TypeLivraison.STANDARD: 2.5,  # Zone large
    TypeLivraison.EXPRESS: 1.5,   # Zone moyenne
    TypeLivraison.SAMEDAY: 1.0,   # Zone restreinte
}

# Default top_k results
DEFAULT_TOP_K = 5

# =============================================================================
# CRITERIA DEFINITIONS
# =============================================================================
# Ordre: [proximité, capacité, type_véhicule, réputation]
CRITERIA_NAMES = [
    "proximite_geographique",  # Distance (cost criterion - to minimize)
    "capacite",                # Capacity (benefit criterion - to maximize)
    "type_vehicule",           # Vehicle type (benefit criterion - to maximize)
    "reputation",              # Reputation (benefit criterion - to maximize)
]

# Criteria types (True = benefit/maximize, False = cost/minimize)
CRITERIA_TYPES = {
    "proximite_geographique": False,  # Cost - minimize distance
    "capacite": True,                 # Benefit - maximize capacity
    "type_vehicule": True,            # Benefit - maximize vehicle capability
    "reputation": True,               # Benefit - maximize reputation
}
