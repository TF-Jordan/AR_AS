#!/bin/bash
# ==============================================================================
# Script pour préparer les wheels Python locaux
# ==============================================================================
# Ce script télécharge tous les packages dans un dossier wheels/
# Les builds Docker suivants utiliseront ces packages en local (pas de download)
#
# Usage: ./scripts/prepare-wheels.sh
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WHEELS_DIR="$PROJECT_DIR/wheels"

echo "=== Préparation des wheels Python ==="
echo "Dossier projet: $PROJECT_DIR"
echo "Dossier wheels: $WHEELS_DIR"

# Créer le dossier wheels
mkdir -p "$WHEELS_DIR"

# Vérifier si pip est disponible
if ! command -v pip &> /dev/null; then
    echo "Erreur: pip n'est pas installé"
    exit 1
fi

echo ""
echo "=== Téléchargement des packages ==="

# Télécharger tous les wheels
pip download \
    --dest "$WHEELS_DIR" \
    --requirement "$PROJECT_DIR/requirements.txt" \
    --platform manylinux2014_x86_64 \
    --python-version 311 \
    --only-binary=:all: \
    2>/dev/null || pip download \
    --dest "$WHEELS_DIR" \
    --requirement "$PROJECT_DIR/requirements.txt"

echo ""
echo "=== Wheels téléchargés ==="
ls -lh "$WHEELS_DIR" | head -20
echo "..."
echo "Total: $(ls -1 "$WHEELS_DIR" | wc -l) fichiers"
echo ""
echo "=== Terminé ==="
echo "Les wheels sont prêts dans: $WHEELS_DIR"
echo "Lancez maintenant: docker compose build"
